import os.path
import re

import matplotlib.pyplot as plt
class DiagramPlotter(object):
    def __init__(self, files):
        self.files = []
        self.save_path = "plots"
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path, exist_ok=True)
        for file in files:
                self.files.append(file)

    def create_image_name_from_path(self, file_path):
        """
        Dynamically extracts the last two folder names in a file path and creates a name for an image.

        Parameters:
        file_path (str): The file path string.

        Returns:
        str: The generated image name.
        """
        # Normalize and split the path
        normalized_path = os.path.normpath(file_path)
        parts = normalized_path.split(os.sep)

        # Ensure the path has at least two parts to extract
        if len(parts) >= 2:
            folder_1 = parts[-2]  # Second to last folder
            folder_2 = parts[-3]  # Third to last folder
            image_name = f"{folder_2}_{folder_1}_image.png"
            return image_name
        else:
            raise ValueError("Path must contain at least two directories.")

    def create_label_name_from_path(self, file_path):
        """
        Dynamically extracts the last two folder names in a file path and creates a name for an image.

        Parameters:
        file_path (str): The file path string.

        Returns:
        str: The generated image name.
        """
        # Normalize and split the path
        normalized_path = os.path.normpath(file_path)
        parts = normalized_path.split(os.sep)

        # Ensure the path has at least two parts to extract
        if len(parts) >= 2:
            folder_1 = parts[-2]  # Second to last folder
            folder_2 = parts[-3]  # Third to last folder
            image_name = f"{folder_2}"
            return image_name
        else:
            raise ValueError("Path must contain at least two directories.")

    def plot_file(self):
        """
                      Extracts the percentage progress and steps, and plots the data.

                      Parameters:
                      file_path (str): Path to the log file.

                      Returns:
                      None
                      """
        for file_path in self.files:

            percent_pattern = re.compile(r"Percent Routes Found: (\d+\.?\d*)%")
            percentages = []
            steps = []

            with open(file_path, 'r') as file:
                step_count = 0
                for line in file:
                    match = percent_pattern.search(line)
                    if match:
                        percent_found = float(match.group(1))
                        step_count += 1
                        percentages.append(percent_found)
                        steps.append(step_count)
                    if 100.0 in percentages:
                        break

            # Plotting the diagram
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

            # Check if 100% was achieved
            if 100.0 in percentages:
                print(f"Percent Routes Found reached 100% in {steps[percentages.index(100.0)]} steps.")
            else:
                print("Percent Routes Found never reached 100%.")

    def plot_files(self):
        """
        Extracts the percentage progress and steps from multiple files and plots the data on a single plot.

        Returns:
        None
        """
        percent_pattern = re.compile(r"Percent Routes Found: (\d+\.?\d*)%")
        folder_names = []
        # Create a single figure for all files
        plt.figure(figsize=(10, 6))

        for file_path in self.files:
            percentages = []
            steps = []
            normalized_path = os.path.normpath(file_path)
            parts = normalized_path.split(os.sep)

            # Ensure the path has at least two parts to extract
            if len(parts) >= 2:
                folder_1 = parts[-2]  # Second to last folder
                folder_2 = parts[-3]  # Third to last folder

                folder_names.append(folder_1)



            with open(file_path, 'r') as file:
                step_count = 0
                for line in file:
                    match = percent_pattern.search(line)
                    if match:
                        percent_found = float(match.group(1))
                        step_count += 1
                        percentages.append(percent_found)
                        steps.append(step_count)
                    if step_count > 55:
                       break
                    #if 100.0 in percentages:
                     #   break

            # Plot the data for this file
            plt.plot(
                steps,
                percentages,
                marker='o',
                linestyle='-',
                label=self.create_label_name_from_path(file_path),  # Use the file name as the legend label
            )

            # Check if 100% was achieved
            if 100.0 in percentages:
                print(
                    f"File {file_path}: Percent Routes Found reached 100% in {steps[percentages.index(100.0)]} steps.")
            else:
                print(f"File {file_path}: Percent Routes Found never reached 100%.")

        plt.title('Percent Routes Found vs. Steps (All Files)', fontsize=16)
        plt.xlabel('Steps', fontsize=16)
        plt.ylabel('Percent Routes Found (%)', fontsize=16)
        plt.xticks(range(0, max(steps) + 1, max(1, len(steps) // 10)), fontsize=16)
        plt.yticks(range(0, 101, 10), fontsize=16)
        plt.grid(True)
        plt.legend(fontsize=16)
        plt.tight_layout()
        # Normalize and split the path
        all_same = all(x == folder_names[0] for x in folder_names)
        if all_same:
            rest_api = folder_names[0]
        else:
            rest_api = ""



        name =(f"o1_{rest_api}_combined_progress_plot.png")

        # Save the figure
        save_path = os.path.join(self.save_path, name)
        plt.savefig(save_path)
        print(f"Plot saved to {save_path}")
        plt.show()

    def plot_files_parameters(self):
        """
        Extracts the percentage progress and steps from multiple files and plots the data on a single plot.

        Returns:
        None
        """
        import re

        percent_pattern = re.compile(r"(Percent Parameters Found|Percent Parameters Keys Found): (\d+\.?\d*)%")
        folder_names = []
        # Create a single figure for all files
        plt.figure(figsize=(10, 6))
        steps =[]

        for file_path in self.files:
            percentages = []
            steps = []
            normalized_path = os.path.normpath(file_path)
            parts = normalized_path.split(os.sep)

            # Ensure the path has at least two parts to extract
            if len(parts) >= 2:
                folder_1 = parts[-2]  # Second to last folder
                folder_2 = parts[-3]  # Third to last folder

                folder_names.append(folder_1)



            with open(file_path, 'r') as file:
                step_count = 0
                for line in file:
                    match = percent_pattern.search(line)
                    if match:
                        percent_found = float(match.group(1))
                        step_count += 1
                        percentages.append(percent_found)
                        steps.append(step_count)
                    #if step_count > 165:
                    #   break
                    if 100.0 in percentages:
                        break

            # Plot the data for this file
            plt.plot(
                steps,
                percentages,
                marker='o',
                linestyle='-',
                label=self.create_label_name_from_path(file_path),  # Use the file name as the legend label
            )

            # Check if 100% was achieved
            if 100.0 in percentages:
                print(
                    f"File {file_path}: Percent  Parameters reached 100% in {steps[percentages.index(100.0)]} steps.")
            else:
                print(f"File {file_path}: Percent  Parameters never reached 100%.")

        plt.title('Percent Parameters Found vs. Steps (All Files)', fontsize=16)
        plt.xlabel('Steps', fontsize=16)
        plt.ylabel('Percent Parameters Found (%)', fontsize=16)
        plt.xticks(range(0, max(steps) + 1, max(1, len(steps) // 10)), fontsize=16)
        plt.yticks(range(0, 101, 10), fontsize=16)
        plt.grid(True)
        plt.legend(fontsize=16)
        plt.tight_layout()
        # Normalize and split the path
        all_same = all(x == folder_names[0] for x in folder_names)
        if all_same:
            rest_api = folder_names[0]
        else:
            rest_api = ""



        name =(f"{rest_api}_combined_progress_percentages_plot.png")

        # Save the figure
        save_path = os.path.join(self.save_path, name)
        plt.savefig(save_path)
        print(f"Plot saved to {save_path}")
        plt.show()


if __name__ == "__main__":
    dp= DiagramPlotter([
        "/home/diana/Desktop/masterthesis/00/hackingBuddyGPT/src/hackingBuddyGPT/usecases/web_api_testing/documentation/openapi_spec/chain_of_thought/openbrewerydb/2025-02-13_10-48-59.txt",
        "/home/diana/Desktop/masterthesis/00/hackingBuddyGPT/src/hackingBuddyGPT/usecases/web_api_testing/documentation/openapi_spec/tree_of_thought/openbrewerydb/2025-02-13_14-55-47.txt",
        "/home/diana/Desktop/masterthesis/00/hackingBuddyGPT/src/hackingBuddyGPT/usecases/web_api_testing/documentation/openapi_spec/in_context/openbrewerydb/2025-02-13_12-49-53.txt",

    ])
    dp.plot_files()

    '''
        "/home/diana/Desktop/masterthesis/00/hackingBuddyGPT/src/hackingBuddyGPT/usecases/web_api_testing/documentation/openapi_spec/chain_of_thought/openbrewerydb/2025-02-13_10-48-59.txt", 
    "/home/diana/Desktop/masterthesis/00/hackingBuddyGPT/src/hackingBuddyGPT/usecases/web_api_testing/documentation/openapi_spec/tree_of_thought/openbrewerydb/2025-02-13_14-55-47.txt", 
    "/home/diana/Desktop/masterthesis/00/hackingBuddyGPT/src/hackingBuddyGPT/usecases/web_api_testing/documentation/openapi_spec/in_context/openbrewerydb/2025-02-13_12-49-53.txt", 

    
    "/home/diana/Desktop/masterthesis/00/hackingBuddyGPT/src/hackingBuddyGPT/usecases/web_api_testing/documentation/openapi_spec/chain_of_thought/randomusergenerator/2025-02-13_10-58-35.txt",
    "/home/diana/Desktop/masterthesis/00/hackingBuddyGPT/src/hackingBuddyGPT/usecases/web_api_testing/documentation/openapi_spec/in_context/randomusergenerator/2025-02-13_12-49-56.txt", 
    "/home/diana/Desktop/masterthesis/00/hackingBuddyGPT/src/hackingBuddyGPT/usecases/web_api_testing/documentation/openapi_spec/in_context/randomusergenerator/2025-02-13_12-49-56.txt"
    
    
    "/home/diana/Desktop/masterthesis/00/hackingBuddyGPT/src/hackingBuddyGPT/usecases/web_api_testing/documentation/openapi_spec/tree_of_thought/reqres/2025-02-13_12-38-38.txt"
    "/home/diana/Desktop/masterthesis/00/hackingBuddyGPT/src/hackingBuddyGPT/usecases/web_api_testing/documentation/openapi_spec/in_context/reqres/2025-02-13_15-05-08.txt",

    
    
    '''


