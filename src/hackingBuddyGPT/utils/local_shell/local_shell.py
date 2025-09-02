from dataclasses import dataclass, field
from typing import Optional, Tuple
import time
import uuid
import subprocess
import re
import signal
import getpass

from hackingBuddyGPT.utils.configurable import configurable

@configurable("local_shell", "attaches to a running local shell inside tmux using tmux")
@dataclass
class LocalShellConnection:
    tmux_session: str = field(metadata={"help": "tmux session name of the running shell inside tmux"})
    delay: float = field(default=0.5, metadata={"help": "delay between commands"})
    max_wait: int = field(default=300, metadata={"help": "maximum wait time for command completion"})
    
    # Static attributes for connection info
    username: str = field(default_factory=getpass.getuser, metadata={"help": "username for the connection"})
    password: str = field(default="", metadata={"help": "password for the connection"})
    host: str = field(default="localhost", metadata={"help": "host for the connection"})
    hostname: str = field(default="localhost", metadata={"help": "hostname for the connection"})
    port: Optional[int] = field(default=None, metadata={"help": "port for the connection"})
    keyfilename: str = field(default="", metadata={"help": "key filename for the connection"})
    
    # Internal state
    last_output_hash: Optional[int] = field(default=None, init=False)
    _initialized: bool = field(default=False, init=False)

    def init(self):
        if not self.check_session():
            raise RuntimeError(f"Tmux session '{self.tmux_session}' does not exist. Please create it first or use an existing session name.")
        else:
            print(f"Connected to existing tmux session: {self.tmux_session}")
            self._initialized = True

    def new_with(self, *, tmux_session=None, delay=None, max_wait=None) -> "LocalShellConnection":
        return LocalShellConnection(
            tmux_session=tmux_session or self.tmux_session,
            delay=delay or self.delay,
            max_wait=max_wait or self.max_wait,
        )

    def run(self, cmd, *args, **kwargs) -> Tuple[str, str, int]:
        """
        Run a command and return (stdout, stderr, return_code).
        This is the main interface method that matches the project pattern.
        """
        if not self._initialized:
            self.init()
        
        if not cmd.strip():
            return "", "", 0
        
        try:
            output = self.run_with_unique_markers(cmd)
            
            return output, "", 0
        except Exception as e:
            return "", str(e), 1

    def send_command(self, command):
        """Send a command to the tmux session."""
        try:
            subprocess.run(['tmux', 'send-keys', '-t', self.tmux_session, command, 'Enter'], check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to send command to tmux: {e}")

    def capture_output(self, history_lines=10000):
        """Capture the entire tmux pane content including scrollback."""
        try:
            # Capture with history to get more content
            result = subprocess.run(
                ['tmux', 'capture-pane', '-t', self.tmux_session, '-p', '-S', f'-{history_lines}'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to capture tmux output: {e}")

    def get_cursor_position(self):
        """Get cursor position to detect if command is still running."""
        try:
            result = subprocess.run(
                ['tmux', 'display-message', '-t', self.tmux_session, '-p', '#{cursor_x},#{cursor_y}'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    def wait_for_command_completion(self, timeout=None, check_interval=0.5):
        """
        Advanced method to wait for command completion using multiple indicators.
        """
        if timeout is None:
            timeout = self.max_wait
        
        start_time = time.time()
        last_output_hash = None
        last_cursor_pos = None
        stable_count = 0
        min_stable_time = 1.5  # Reduced for faster detection
        
        while time.time() - start_time < timeout:
            # Use hash for large outputs to detect changes more efficiently
            current_output = self.capture_output(1000)  # Smaller buffer for speed
            current_output_hash = hash(current_output)
            current_cursor = self.get_cursor_position()
            
            # Check if output and cursor position are stable
            if (current_output_hash == last_output_hash and 
                current_cursor == last_cursor_pos and 
                current_cursor is not None):
                stable_count += 1
                
                # If stable for enough cycles, check for prompt
                if stable_count >= (min_stable_time / check_interval):
                    if self._has_prompt_at_end(current_output):
                        return True
            else:
                stable_count = 0
            
            last_output_hash = current_output_hash
            last_cursor_pos = current_cursor
            
            time.sleep(check_interval)
        
        return False

    def _has_prompt_at_end(self, output):
        if not output.strip():
            return False
            
        lines = output.strip().split('\n')
        if not lines:
            return False
            
        last_line = lines[-1].strip()
        
        prompt_patterns = [
            r'.*[$#]\s*$',                    # Basic $ or # prompts
            r'.*>\s*$',                       # > prompts
            r'.*@.*:.*[$#]\s*$',             # user@host:path$ format
            r'.*@.*:.*>\s*$',                # user@host:path> format
            r'^\S+:\S*[$#]\s*$',             # Simple host:path$ format
            r'.*\$\s*$',                     # Ends with $ (catch-all)
            r'.*#\s*$',                      # Ends with # (catch-all)
        ]
        
        for pattern in prompt_patterns:
            if re.match(pattern, last_line):
                return True
        
        if len(last_line) < 100 and any(char in last_line for char in ['$', '#', '>', ':']):
            if not any(keyword in last_line.lower() for keyword in 
                      ['error', 'warning', 'failed', 'success', 'completed', 'finished']):
                return True
                
        return False

    def run_with_unique_markers(self, command):
        """Run command using unique markers - improved version for large outputs."""
        start_marker = f"CMDSTART{uuid.uuid4().hex[:8]}"
        end_marker = f"CMDEND{uuid.uuid4().hex[:8]}"
        
        try:
            self.send_command(f"echo '{start_marker}'")
            time.sleep(0.5)
            
            self.send_command(command)
            
            if not self.wait_for_command_completion():
                raise RuntimeError(f"Command timed out after {self.max_wait}s")
            
            self.send_command(f"echo '{end_marker}'")
            time.sleep(0.8)
            
            final_output = self.capture_output(50000)
            
            # Extract content between markers
            result = self._extract_between_markers(final_output, start_marker, end_marker, command)
            return result
            
        except Exception as e:
            return self.run_simple_fallback(command)

    def _extract_between_markers(self, output, start_marker, end_marker, original_command):
        lines = output.splitlines()
        start_idx = -1
        end_idx = -1
        
        for i, line in enumerate(lines):
            if start_marker in line:
                start_idx = i
            elif end_marker in line and start_idx != -1:
                end_idx = i
                break
        
        if start_idx == -1 or end_idx == -1:
            return self.run_simple_fallback(original_command)
        
        extracted_lines = []
        for i in range(start_idx + 1, end_idx):
            line = lines[i]
            if not self._is_command_echo(line, original_command):
                extracted_lines.append(line)
        
        return '\n'.join(extracted_lines).strip()

    def _is_command_echo(self, line, command):
        stripped = line.strip()
        if not stripped:
            return False
        
        for prompt_char in ['$', '#', '>']:
            if prompt_char in stripped:
                after_prompt = stripped.split(prompt_char, 1)[-1].strip()
                if after_prompt == command:
                    return True
        
        return stripped == command

    def run_simple_fallback(self, command):
        try:
            subprocess.run(['tmux', 'set-option', '-t', self.tmux_session, 'history-limit', '50000'], 
                         capture_output=True)
            
            clear_marker = f"__CLEAR_{uuid.uuid4().hex[:8]}__"
            self.send_command('clear')
            time.sleep(0.3)
            self.send_command(f'echo "{clear_marker}"')
            time.sleep(0.3)
            
            self.send_command(command)
            
            self.wait_for_command_completion()
            
            end_marker = f"__END_{uuid.uuid4().hex[:8]}__"
            self.send_command(f'echo "{end_marker}"')
            time.sleep(0.5)
            
            output = self.capture_output(50000)
            
            lines = output.splitlines()
            start_idx = -1
            end_idx = -1
            
            for i, line in enumerate(lines):
                if clear_marker in line:
                    start_idx = i
                elif end_marker in line and start_idx != -1:
                    end_idx = i
                    break
            
            if start_idx != -1 and end_idx != -1:
                result_lines = lines[start_idx + 1:end_idx]
                if result_lines and command in result_lines[0]:
                    result_lines = result_lines[1:]
                result = '\n'.join(result_lines).strip()
            else:
                result = self._extract_recent_output(output, command)
            
            subprocess.run(['tmux', 'set-option', '-t', self.tmux_session, 'history-limit', '10000'], 
                         capture_output=True)
            
            return result
            
        except Exception as e:
            subprocess.run(['tmux', 'set-option', '-t', self.tmux_session, 'history-limit', '10000'], 
                         capture_output=True)
            raise RuntimeError(f"Error executing command: {e}")

    def _extract_recent_output(self, output, command):
        lines = output.splitlines()
        
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i]
            if command in line and any(prompt in line for prompt in ['$', '#', '>', '└─']):
                return '\n'.join(lines[i + 1:]).strip()
        
        return '\n'.join(lines[-50:]).strip() if lines else ""

    def run_with_timeout(self, command, timeout=60):
        old_max_wait = self.max_wait
        self.max_wait = timeout
        try:
            return self.run(command)
        finally:
            self.max_wait = old_max_wait

    def interrupt_command(self):
        try:
            subprocess.run(['tmux', 'send-keys', '-t', self.tmux_session, 'C-c'], check=True)
            time.sleep(1)
            return True
        except subprocess.CalledProcessError:
            return False

    def check_session(self):
        try:
            result = subprocess.run(
                ['tmux', 'list-sessions', '-F', '#{session_name}'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            
            session_names = result.stdout.strip().split('\n')
            return self.tmux_session in session_names
            
        except subprocess.CalledProcessError:
            return False

    def get_session_info(self):
        try:
            result = subprocess.run(
                ['tmux', 'display-message', '-t', self.tmux_session, '-p', 
                 'Session: #{session_name}, Window: #{window_name}, Pane: #{pane_index}'],
                stdout=subprocess.PIPE,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "Session info unavailable"

