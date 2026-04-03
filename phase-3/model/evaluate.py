import json
import pickle
import numpy as np
import matplotlib.pyplot as plt

# =============================
# LOAD DATA + MODEL
# =============================
data = json.load(open("attack_dataset.json"))
Q = pickle.load(open("q_table.pkl","rb"))

# =============================
# STATE FUNCTION
# =============================
def get_state(row):
    return int(f"{int(row['rate']>10)}{row['anomaly']}{int(not row['known'])}{row['repeat']}",2)

# =============================
# METRICS CALCULATION
# =============================
TP = FP = TN = FN = 0

for row in data:
    s = get_state(row)
    action = np.argmax(Q[s])

    predicted_attack = (action == 2)
    actual_attack = bool(row["is_attack"])

    if predicted_attack and actual_attack:
        TP += 1
    elif predicted_attack and not actual_attack:
        FP += 1
    elif not predicted_attack and not actual_attack:
        TN += 1
    else:
        FN += 1

# =============================
# METRICS
# =============================
accuracy  = (TP + TN) / len(data)
precision = TP / (TP + FP) if (TP + FP) else 0
recall    = TP / (TP + FN) if (TP + FN) else 0
f1        = 2 * precision * recall / (precision + recall) if (precision + recall) else 0

print("\n===== EVALUATION RESULTS =====")
print(f"TP={TP}, FP={FP}, TN={TN}, FN={FN}")
print(f"Accuracy : {accuracy:.3f}")
print(f"Precision: {precision:.3f}")
print(f"Recall   : {recall:.3f}")
print(f"F1 Score : {f1:.3f}")

# =============================
# GRAPH 1: CONFUSION MATRIX
# =============================
cm = [[TP, FP],
      [FN, TN]]

plt.figure()
plt.imshow(cm)
plt.title("Confusion Matrix")

plt.xticks([0,1], ["Attack","Normal"])
plt.yticks([0,1], ["Attack","Normal"])

plt.xlabel("Predicted")
plt.ylabel("Actual")

for i in range(2):
    for j in range(2):
        plt.text(j, i, cm[i][j], ha='center', va='center')

plt.colorbar()

# =============================
# GRAPH 2: METRICS BAR
# =============================
plt.figure()
metrics = ["Accuracy","Precision","Recall","F1"]
values  = [accuracy, precision, recall, f1]

plt.bar(metrics, values)
plt.title("Model Performance")
plt.ylabel("Score")
plt.ylim(0,1)

# =============================
# GRAPH 3: CLASS DISTRIBUTION
# =============================
attacks = sum(1 for d in data if d["is_attack"])
normal  = len(data) - attacks

plt.figure()
plt.bar(["Attack","Normal"], [attacks, normal])
plt.title("Dataset Distribution")

# =============================
# SHOW ALL
# =============================
plt.show()