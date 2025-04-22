import matplotlib.pyplot as plt
import numpy as np
from sklearn import metrics
total_num_of_vuls = 22
# Define the number of vulnerabilities detected
TP =  17 # Detected vulnerabilities
FN = total_num_of_vuls - TP  # Missed vulnerabilities
FP = 5  # Incorrectly flagged vulnerabilities
TN = 40 - total_num_of_vuls  # Correctly identified non-vulnerabilities

# Confusion matrix values: [[TN, FP], [FN, TP]]
confusion_matrix = np.array([[TN, FP],  # True Negatives, False Positives
                             [FN, TP]])  # False Negatives, True Positives

# Create and plot the confusion matrix
cm_display = metrics.ConfusionMatrixDisplay(confusion_matrix=confusion_matrix, display_labels=["No Vuln", "Vuln"])
cm_display.plot(cmap="Blues")

# Compute evaluation metrics
accuracy = ((TP + TN) / (TP + TN + FP + FN) )*100
precision = (TP / (TP + FP)) *100 if (TP + FP) > 0 else 0
recall = (TP / (TP + FN)) * 100 if (TP + FN) > 0 else 0
f1 = (2 * (precision * recall) / (precision + recall)) *100 if (precision + recall) > 0 else 0

print(f'accuracy:{accuracy}, precision:{precision}, recall:{recall}, f1:{f1}')
plt.savefig("crapi_confusion_matrix.png")
