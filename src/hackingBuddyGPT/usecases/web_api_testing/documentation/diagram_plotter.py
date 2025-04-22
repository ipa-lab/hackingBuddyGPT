import os
import re
import matplotlib.pyplot as plt


class DiagramPlotter:
    """
    A class for visualizing progress from log files generated during API testing.

    It plots percentage-based metrics such as "Percent Routes Found" or "Percent Parameters Found"
    against the number of steps, and supports saving individual and combined plots.

    Attributes:
        files (list): List of file paths containing log data.
        save_path (str): Directory path where the plots will be saved.
    """

    def __init__(self, files):
        """
        Initializes the DiagramPlotter with a list of files and ensures the save directory exists.

        Args:
            files (list): List of strings, each representing the path to a log file.
        """
        self.files = []
        self.save_path = "plots"
        os.makedirs(self.save_path, exist_ok=True)
        for file in files:
            self.files.append(file)

    def create_image_name_from_path(self, file_path):
        """
        Generates an image name from the last two folder names in a given file path.

        Args:
            file_path (str): The full file path.

        Returns:
            str: Generated image file name.
        """
        parts = os.path.normpath(file_path).split(os.sep)
        if len(parts) >= 3:
            folder_1 = parts[-2]
            folder_2 = parts[-3]
            return f"{folder_2}_{folder_1}_image.png"
        else:
            raise ValueError("Path must contain at least two directories.")

    def create_label_name_from_path(self, file_path):
        """
        Generates a label from the folder name for use in plot legends.

        Args:
            file_path (str): The full file path.

        Returns:
            str: Generated label name.
        """
        parts = os.path.normpath(file_path).split(os.sep)
        if len(parts) >= 3:
            return parts[-2]
        else:
            raise ValueError("Path must contain at least two directories.")

    def plot_file(self):
        """
        Plots the "Percent Routes Found" progression for each file individually and saves the plot.

        Returns:
            None
        """
        pattern = re.compile(r"Percent Routes Found: (\d+\.?\d*)%")

        for file_path in self.files:
            percentages, steps = [], []
            with open(file_path, 'r') as file:
                step_count = 0
                for line in file:
                    match = pattern.search(line)
                    if match:
                        step_count += 1
                        percentages.append(float(match.group(1)))
                        steps.append(step_count)
                    if 100.0 in percentages:
                        break

            plt.figure(figsize=(10, 6))
            plt.plot(steps, percentages, marker='o', linestyle='-', color='b', label='Progress')
            plt.title('Percent Routes Found vs. Steps')
            plt.xlabel('Steps')
            plt.ylabel('Percent Routes Found (%)')
            plt.xticks(range(1, len(steps) + 1, max(1, len(steps) // 10)))
            plt.yticks(range(0, 101, 10))
            plt.grid(True)
            plt.legend()
            plt.savefig(os.path.join(self.save_path, self.create_image_name_from_path(file_path)))

            if 100.0 in percentages:
                print(f"Percent Routes Found reached 100% in {steps[percentages.index(100.0)]} steps.")
            else:
                print("Percent Routes Found never reached 100%.")

    def plot_files(self):
        """
        Plots "Percent Routes Found" for multiple log files on a single combined chart.

        Returns:
            None
        """
        pattern = re.compile(r"Percent Routes Found: (\d+\.?\d*)%")
        folder_names = []
        plt.figure(figsize=(10, 6))
        global_steps = []

        for file_path in self.files:
            percentages, steps = [], []
            parts = os.path.normpath(file_path).split(os.sep)
            if len(parts) >= 3:
                folder_names.append(parts[-2])

            with open(file_path, 'r') as file:
                step_count = 0
                for line in file:
                    match = pattern.search(line)
                    if match:
                        step_count += 1
                        percentages.append(float(match.group(1)))
                        steps.append(step_count)
                    if step_count > 55:
                        break

            global_steps = steps  # Track for common axis scaling
            plt.plot(
                steps,
                percentages,
                marker='o',
                linestyle='-',
                label=self.create_label_name_from_path(file_path)
            )

            if 100.0 in percentages:
                print(f"File {file_path}: 100% reached in {steps[percentages.index(100.0)]} steps.")
            else:
                print(f"File {file_path}: Never reached 100%.")

        plt.title('Percent Routes Found vs. Steps (All Files)', fontsize=16)
        plt.xlabel('Steps', fontsize=16)
        plt.ylabel('Percent Routes Found (%)', fontsize=16)
        plt.xticks(range(0, max(global_steps) + 1, max(1, len(global_steps) // 10)), fontsize=14)
        plt.yticks(range(0, 101, 10), fontsize=14)
        plt.grid(True)
        plt.legend(fontsize=12)
        plt.tight_layout()

        rest_api = folder_names[0] if all(x == folder_names[0] for x in folder_names) else ""
        name = f"o1_{rest_api}_combined_progress_plot.png"
        save_path = os.path.join(self.save_path, name)
        plt.savefig(save_path)
        print(f"Plot saved to {save_path}")
        plt.show()

    def plot_files_parameters(self):
        """
        Plots "Percent Parameters Found" or "Percent Parameters Keys Found" for multiple files on one chart.

        Returns:
            None
        """
        pattern = re.compile(r"(Percent Parameters Found|Percent Parameters Keys Found): (\d+\.?\d*)%")
        folder_names = []
        plt.figure(figsize=(10, 6))
        global_steps = []

        for file_path in self.files:
            percentages, steps = [], []
            parts = os.path.normpath(file_path).split(os.sep)
            if len(parts) >= 3:
                folder_names.append(parts[-2])

            with open(file_path, 'r') as file:
                step_count = 0
                for line in file:
                    match = pattern.search(line)
                    if match:
                        step_count += 1
                        percentages.append(float(match.group(2)))
                        steps.append(step_count)
                    if 100.0 in percentages:
                        break

            global_steps = steps
            plt.plot(
                steps,
                percentages,
                marker='o',
                linestyle='-',
                label=self.create_label_name_from_path(file_path)
            )

            if 100.0 in percentages:
                print(f"File {file_path}: 100% parameters found in {steps[percentages.index(100.0)]} steps.")
            else:
                print(f"File {file_path}: Parameters never reached 100%.")

        plt.title('Percent Parameters Found vs. Steps (All Files)', fontsize=16)
        plt.xlabel('Steps', fontsize=16)
        plt.ylabel('Percent Parameters Found (%)', fontsize=16)
        plt.xticks(range(0, max(global_steps) + 1, max(1, len(global_steps) // 10)), fontsize=14)
        plt.yticks(range(0, 101, 10), fontsize=14)
        plt.grid(True)
        plt.legend(fontsize=12)
        plt.tight_layout()

        rest_api = folder_names[0] if all(x == folder_names[0] for x in folder_names) else ""
        name = f"{rest_api}_combined_progress_percentages_plot.png"
        save_path = os.path.join(self.save_path, name)
        plt.savefig(save_path)
        print(f"Plot saved to {save_path}")
        plt.show()
