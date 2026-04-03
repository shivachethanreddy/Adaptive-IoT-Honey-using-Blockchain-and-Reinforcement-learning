import numpy as np
import json
import pickle

# Load real attack dataset from Month 2
dataset = json.load(open("attack_dataset.json"))

# Q-table: 16 states x 3 actions
# States : 2^4 = 16 (4 binary features)
# Actions: 0=allow, 1=warn, 2=block
Q = np.zeros((16, 3))

alpha   = 0.1   # learning rate
gamma   = 0.9   # discount factor
epsilon = 0.2   # exploration rate

def get_state(rate, anomaly, known, repeat):
    # Convert 4 binary features to a single state index 0-15
    b = f"{int(rate > 10)}{int(anomaly)}{int(not known)}{int(repeat)}"
    return int(b, 2)

def get_reward(action, is_attack):
    if action == 2 and is_attack:      return  1.0  # correct block
    if action == 0 and not is_attack:  return  0.5  # correct allow
    if action == 2 and not is_attack:  return -1.0  # false positive
    if action == 0 and is_attack:      return -0.5  # missed attack
    return 0.0  # warn — neutral

print("Training RL agent on Month 2 attack data...")
print(f"Dataset size: {len(dataset)} rows")

rewards_per_episode = []

for episode in range(1000):
    total_reward = 0
    for row in dataset:
        s = get_state(row["rate"], row["anomaly"],
                      row["known"], row["repeat"])

        # Epsilon-greedy: explore or exploit
        if np.random.rand() < epsilon:
            a = np.random.randint(3)
        else:
            a = int(np.argmax(Q[s]))

        r = get_reward(a, row["is_attack"])
        total_reward += r

        # Q-learning update
        Q[s, a] += alpha * (r + gamma * np.max(Q[s]) - Q[s, a])

    rewards_per_episode.append(total_reward)
    if (episode + 1) % 100 == 0:
        avg = sum(rewards_per_episode[-100:]) / 100
        print(f"  Episode {episode+1}/1000 | Avg reward: {avg:.2f}")

# Save trained Q-table
pickle.dump(Q, open("q_table.pkl", "wb"))
print("\nTraining complete — q_table.pkl saved")

# Test accuracy on dataset
correct = 0
for row in dataset:
    s = get_state(row["rate"], row["anomaly"],
                  row["known"], row["repeat"])
    a = int(np.argmax(Q[s]))
    predicted_block = (a == 2)
    actual_attack   = bool(row["is_attack"])
    if predicted_block == actual_attack:
        correct += 1

accuracy = correct / len(dataset) * 100
print(f"Accuracy on training data: {accuracy:.1f}%")
print("\nQ-table (rows=states, cols=allow/warn/block):")
print(np.round(Q, 2))