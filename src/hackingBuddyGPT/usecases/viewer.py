#!/usr/bin/python3

import asyncio
import datetime
import json
import os
import random
import string
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Optional, Union

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from hackingBuddyGPT.usecases.usecase import UseCase, use_case
from hackingBuddyGPT.utils.configurable import parameter
from hackingBuddyGPT.utils.db_storage import DbStorage
from hackingBuddyGPT.utils.db_storage.db_storage import (
    Message,
    MessageStreamPart,
    Run,
    Section,
    ToolCall,
    ToolCallStreamPart,
)
from dataclasses_json import dataclass_json

from hackingBuddyGPT.utils.logging import GlobalLocalLogger, GlobalRemoteLogger

INGRESS_TOKEN = os.environ.get("INGRESS_TOKEN", None)
VIEWER_TOKEN = os.environ.get("VIEWER_TOKEN", random.choices(string.ascii_letters + string.digits, k=32))


BASE_DIR = os.path.dirname(os.path.abspath(__file__)) + "/"
RESOURCE_DIR = BASE_DIR + "../resources/webui"
TEMPLATE_DIR = RESOURCE_DIR + "/templates"
STATIC_DIR = RESOURCE_DIR + "/static"


@dataclass_json
@dataclass(frozen=True)
class MessageRequest:
    follow_run: Optional[int] = None


MessageData = Union[MessageRequest, Run, Section, Message, MessageStreamPart, ToolCall, ToolCallStreamPart]


class MessageType(str, Enum):
    MESSAGE_REQUEST = "MessageRequest"
    RUN = "Run"
    SECTION = "Section"
    MESSAGE = "Message"
    MESSAGE_STREAM_PART = "MessageStreamPart"
    TOOL_CALL = "ToolCall"
    TOOL_CALL_STREAM_PART = "ToolCallStreamPart"

    def get_class(self) -> MessageData:
        return {
            "MessageRequest": MessageRequest,
            "Run": Run,
            "Section": Section,
            "Message": Message,
            "MessageStreamPart": MessageStreamPart,
            "ToolCall": ToolCall,
            "ToolCallStreamPart": ToolCallStreamPart,
        }[self.value]


@dataclass_json
@dataclass
class ControlMessage:
    type: MessageType
    data: MessageData


@dataclass_json
@dataclass(frozen=True)
class ReplayMessage:
    at: datetime.datetime
    message: ControlMessage


@dataclass
class Client:
    websocket: WebSocket
    db: DbStorage

    queue: asyncio.Queue[ControlMessage] = field(default_factory=asyncio.Queue)

    current_run = None
    follow_new_runs = False

    async def send_message(self, message: ControlMessage) -> None:
        await self.websocket.send_text(message.to_json())

    async def send(self, type: MessageType, message: MessageData) -> None:
        await self.send_message(ControlMessage(type, message))

    async def send_messages(self) -> None:
        runs = self.db.get_runs()
        for r in runs:
            await self.send(MessageType.RUN, r)

        while True:
            try:
                msg: ControlMessage = await self.queue.get()
                data = msg.data
                if msg.type == MessageType.MESSAGE_REQUEST:
                    if data.follow_run is not None:
                        await self.switch_to_run(data.follow_run)

                elif msg.type == MessageType.RUN:
                    await self.send_message(msg)

                elif msg.type in MessageType:
                    if not hasattr(data, "run_id"):
                        print("msg has no run_id", data)
                    if self.current_run == data.run_id:
                        await self.send_message(msg)

                else:
                    print(f"Unknown message type: {msg.type}")

            except WebSocketDisconnect:
                break

            except Exception as e:
                print(f"Error sending message: {e}")
                raise e

    async def receive_messages(self) -> None:
        while True:
            try:
                msg = await self.websocket.receive_json()
                if msg["type"] != MessageType.MESSAGE_REQUEST:
                    print(f"Unknown message type: {msg['type']}")
                    continue

                if "data" not in msg:
                    print("Invalid message")
                    continue

                data = msg["data"]

                if "follow_run" not in data:
                    print("Invalid message")
                    continue

                message = ControlMessage(
                    type=MessageType.MESSAGE_REQUEST,
                    data=MessageRequest(int(data["follow_run"])),
                )
                # we don't process the message here, as having all message processing done in lockstep in the send_messages
                # function means that we don't have to worry about race conditions between reading from the database and
                # incoming messages
                await self.queue.put(message)
            except Exception as e:
                print(f"Error receiving message: {e}")
                raise e

    async def switch_to_run(self, run_id: int):
        self.current_run = run_id
        messages = self.db.get_messages_by_run(run_id)

        tool_calls = list(self.db.get_tool_calls_by_run(run_id))
        tool_calls_per_message = dict()
        for tc in tool_calls:
            if tc.message_id not in tool_calls_per_message:
                tool_calls_per_message[tc.message_id] = []
            tool_calls_per_message[tc.message_id].append(tc)

        sections: list[Section] = list(self.db.get_sections_by_run(run_id))
        sections_starting_with_message = dict()
        for s in sections:
            if s.from_message not in sections_starting_with_message:
                sections_starting_with_message[s.from_message] = []
            sections_starting_with_message[s.from_message].append(s)

        for msg in messages:
            if msg.id in sections_starting_with_message:
                for s in sections_starting_with_message[msg.id]:
                    await self.send(MessageType.SECTION, s)
                    sections.remove(s)
            await self.send(MessageType.MESSAGE, msg)
            if msg.id in tool_calls_per_message:
                for tc in tool_calls_per_message[msg.id]:
                    await self.send(MessageType.TOOL_CALL, tc)
                    tool_calls.remove(tc)

        for tc in tool_calls:
            await self.send(MessageType.TOOL_CALL, tc)

        for s in sections:
            await self.send(MessageType.SECTION, s)


@use_case("Webserver for (live) log viewing")
class Viewer(UseCase):
    """
    TODOs:
    - [ ] This server needs to be as async as possible to allow good performance, but the database accesses are not yet, might be an issue?
    """
    log: GlobalLocalLogger = None
    log_db: DbStorage = None
    log_server_address: str = "127.0.0.1:4444"
    save_playback_dir: str = ""

    async def save_message(self, message: ControlMessage):
        if not self.save_playback_dir or len(self.save_playback_dir) == 0:
            return

        # check if a file with the name of the message run id already exists in the save_playback_dir
        # if it does, append the message to the json lines file
        # if it doesn't, create a new file with the name of the message run id and write the message to it
        if isinstance(message.data, Run):
            run_id = message.data.id
        elif hasattr(message.data, "run_id"):
            run_id = message.data.run_id
        else:
            raise ValueError("gotten message without run_id", message)

        if not os.path.exists(self.save_playback_dir):
            os.makedirs(self.save_playback_dir)

        file_path = os.path.join(self.save_playback_dir, f"{run_id}.jsonl")
        with open(file_path, "a") as f:
            f.write(ReplayMessage(datetime.datetime.now(), message).to_json() + "\n")

    def run(self, config):
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            app.state.db = self.log_db
            app.state.clients = []

            yield

            for client in app.state.clients:
                await client.websocket.close()

        app = FastAPI(lifespan=lifespan)

        # TODO: re-enable and only allow anything else than localhost when a token is set
        """
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:4444", "ws://localhost:4444", "wss://pwn.reinsperger.org", "https://pwn.reinsperger.org", "https://dumb-halloween-game.reinsperger.org"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        """

        templates = Jinja2Templates(directory=TEMPLATE_DIR)
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

        @app.get('/favicon.ico')
        async def favicon():
            return FileResponse(STATIC_DIR + "/favicon.ico", headers={"Cache-Control": "public, max-age=31536000"})

        @app.get("/", response_class=HTMLResponse)
        async def admin_ui(request: Request):
            return templates.TemplateResponse("index.html", {"request": request})

        @app.websocket("/ingress")
        async def ingress_endpoint(websocket: WebSocket):
            await websocket.accept()
            try:
                while True:
                    # Receive messages from the ingress websocket
                    data = await websocket.receive_json()
                    message_type = MessageType(data["type"])
                    # parse the data according to the message type into the appropriate dataclass
                    message = message_type.get_class().from_dict(data["data"])

                    if message_type == MessageType.RUN:
                        if message.id is None:
                            message.started_at = datetime.datetime.now()
                            message.id = app.state.db.create_run(message.model, message.tag, message.started_at, message.configuration)
                            data["data"]["id"] = message.id  # set the id also in the raw data, so we can properly serialize it to replays
                        else:
                            app.state.db.update_run(message.id, message.model, message.state, message.tag, message.started_at, message.stopped_at, message.configuration)
                        await websocket.send_text(message.to_json())

                    elif message_type == MessageType.MESSAGE:
                        app.state.db.add_or_update_message(message.run_id, message.id, message.conversation, message.role, message.content, message.tokens_query, message.tokens_response, message.duration)

                    elif message_type == MessageType.MESSAGE_STREAM_PART:
                        app.state.db.handle_message_update(message.run_id, message.message_id, message.action, message.content)

                    elif message_type == MessageType.TOOL_CALL:
                        app.state.db.add_tool_call(message.run_id, message.message_id, message.id, message.function_name, message.arguments, message.result_text, message.duration)

                    elif message_type == MessageType.SECTION:
                        app.state.db.add_section(message.run_id, message.id, message.name, message.from_message, message.to_message, message.duration)

                    else:
                        print("UNHANDLED ingress", message)

                    control_message = ControlMessage(type=message_type, data=message)
                    await self.save_message(control_message)
                    for client in app.state.clients:
                        await client.queue.put(control_message)

            except WebSocketDisconnect as e:
                import traceback
                traceback.print_exc()
                print("Ingress WebSocket disconnected")

        @app.websocket("/client")
        async def client_endpoint(websocket: WebSocket):
            await websocket.accept()
            client = Client(websocket, app.state.db)
            app.state.clients.append(client)

            # run the receiving and sending tasks in the background until one of them returns
            tasks = ()
            try:
                tasks = (
                    asyncio.create_task(client.send_messages()),
                    asyncio.create_task(client.receive_messages()),
                )
                await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            except WebSocketDisconnect:
                # read the task exceptions, close remaining tasks
                for task in tasks:
                    if task.exception():
                        print(task.exception())
                    else:
                        task.cancel()
                app.state.clients.remove(client)
                print("Egress WebSocket disconnected")

        import uvicorn
        listen_parts = self.log_server_address.split(":", 1)
        if len(listen_parts) != 2:
            if listen_parts[0].startswith("http://"):
                listen_parts.append("80")
            elif listen_parts[0].startswith("https://"):
                listen_parts.append("443")
            else:
                raise ValueError(f"Invalid log server address (does not contain http/https or a port): {self.log_server_address}")

        listen_host, listen_port = listen_parts[0], int(listen_parts[1])
        if listen_host.startswith("http://"):
            listen_host = listen_host[len("http://"):]
        elif listen_host.startswith("https://"):
            listen_host = listen_host[len("https://"):]
        uvicorn.run(app, host=listen_host, port=listen_port)

    def get_name(self) -> str:
        return "log_viewer"


@use_case("Tool to replay the .jsonl logs generated by the Viewer (not well tested)")
class Replayer(UseCase):
    log: GlobalRemoteLogger = None
    replay_file: str = None
    pause_on_message: bool = False
    pause_on_tool_calls: bool = False
    playback_speed: float = 1.0

    def get_name(self) -> str:
        return "replayer"

    def init(self, configuration):
        self.log.init_websocket()  # we don't want to automatically start a run here

    def run(self):
        recording_start: Optional[datetime.datetime] = None
        replay_start: datetime.datetime = datetime.datetime.now()

        print(f"replaying {self.replay_file}")
        for line in open(self.replay_file, "r"):
            data = json.loads(line)
            msg: ReplayMessage = ReplayMessage.from_dict(data)
            msg.message.type = MessageType(data["message"]["type"])
            msg.message.data = msg.message.type.get_class().from_dict(data["message"]["data"])

            if recording_start is None:
                if msg.message.type != MessageType.RUN:
                    raise ValueError("First message must be a RUN message, is", msg.message.type)
                recording_start = msg.at
                self.log.start_run(msg.message.data.model, msg.message.data.tag, msg.message.data.configuration, msg.at)

            # wait until the message should be sent
            sleep_time = ((msg.at - recording_start) / self.playback_speed) - (datetime.datetime.now() - replay_start)
            if sleep_time.total_seconds() > 3:
                print(msg)
                print(f"sleeping for {sleep_time.total_seconds()}s")
            time.sleep(max(sleep_time.total_seconds(), 0))

            if isinstance(msg.message.data, Run):
                msg.message.data.id = self.log.run.id
            elif hasattr(msg.message.data, "run_id"):
                msg.message.data.run_id = self.log.run.id
            else:
                raise ValueError("Message has no run_id", msg.message.data)

            if self.pause_on_message and msg.message.type == MessageType.MESSAGE \
               or self.pause_on_tool_calls and msg.message.type == MessageType.TOOL_CALL:
                input("Paused, press Enter to continue")
                replay_start = datetime.datetime.now() - (msg.at - recording_start)

            print("sending")
            self.log.send(msg.message.type, msg.message.data)
