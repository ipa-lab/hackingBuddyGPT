import matplotlib.pyplot as plt
import numpy as np
from sklearn import metrics
#total_num_of_vuls = 4
#print(f'total_num_buls:{total_num_of_vuls}')
# Define the number of vulnerabilities detected
TP =  17 # Detected vulnerabilities
FN = 5  # Missed vulnerabilities
FP = 5 # Incorrectly flagged vulnerabilities
TN = 18   # Correctly identified non-vulnerabilities

# Confusion matrix values: [[TN, FP], [FN, TP]]
confusion_matrix = np.array([[TN, FP],  # True Negatives, False Positives
                             [FN, TP]])  # False Negatives, True Positives

# Create and plot the confusion matrix
cm_display = metrics.ConfusionMatrixDisplay(confusion_matrix=confusion_matrix, display_labels=["No Vuln", "Vuln"])
##fig, ax = plt.subplots(figsize=(10, 10))
cm_display.plot(cmap="Blues")
for labels in cm_display.text_.ravel():
    labels.set_fontsize(30)

#ax.tick_params(axis='both', which='major', labelsize=20)  # Adjust to fit
plt.ylabel("True Label", fontsize=16, fontweight='bold')  # Increase y-axis label font size
plt.xlabel("Predicted Label", fontsize=16, fontweight='bold')  # Increase x-axis label font size
# Compute evaluation metrics
accuracy = ((TP + TN) / (TP + TN + FP + FN) )*100
precision = (TP / (TP + FP)) *100 if (TP + FP) > 0 else 0
recall = (TP / (TP + FN)) * 100 if (TP + FN) > 0 else 0
f1 = (2 * (precision * recall) / (precision + recall)) *100 if (precision + recall) > 0 else 0

print(f'accuracy:{accuracy}, precision:{precision}, recall:{recall}, f1:{f1}')
plt.savefig("crapi_confusion_matrix.png")