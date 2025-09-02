import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

# Paths to the SQLite databases and model names
db_info = {
    'openai': './openai.slite3',
    'google': './gemini.sqlite3',
    'meta': './llama.sqlite3'
}

# Total costs for each model
costs = {
    'openai': 8.51,
    'google': 3.29,
    'meta': 4.48
}

# Query to get max flags submitted per run (including zero-flag runs)
flag_query = """
SELECT
  r.run_id,
  COALESCE(f.max_flag_submitted, 0) AS max_flag_submitted
FROM (
  SELECT DISTINCT run_id FROM messages
) AS r
LEFT JOIN (
  SELECT
    run_id,
    MAX(
      CAST(
        SUBSTR(
          result_text,
          INSTR(result_text, '(') + 1,
          INSTR(result_text, '/') - INSTR(result_text, '(') - 1
        ) AS INTEGER
      )
    ) AS max_flag_submitted
  FROM tool_calls
  WHERE
    function_name = 'SubmitFlag'
    AND result_text LIKE 'Flag submitted%'
  GROUP BY run_id
) AS f
ON r.run_id = f.run_id;
"""

# Collect data
results = []
for model, path in db_info.items():
    conn = sqlite3.connect(path)
    df = pd.read_sql_query(flag_query, conn)
    conn.close()
    total_flags = df['max_flag_submitted'].sum()
    total_cost = costs[model]
    cost_per_flag = total_cost / total_flags if total_flags > 0 else None
    results.append({
        'model': model,
        'cost_per_flag': cost_per_flag
    })

# Create DataFrame
result_df = pd.DataFrame(results)

# Create a shorter bar chart: same width, 60% of the default height
fig, ax = plt.subplots(figsize=(6.4, 2.88))
ax.bar(result_df['model'], result_df['cost_per_flag'])
ax.set_ylabel('Cost per Flag ($)')
# Remove xlabel
# ax.set_xlabel('Model')

# Annotate bars with values
for i, row in result_df.iterrows():
    ax.text(i, row['cost_per_flag'] + 0.005, f"{row['cost_per_flag']:.2f}",
            ha='center', va='bottom')

plt.tight_layout()
#
# Create a shorter bar chart: same width, 60% of the default height
fig, ax = plt.subplots(figsize=(6.4, 2.88))

# Plot bars in orange
bars = ax.bar(result_df['model'], result_df['cost_per_flag'], color='orange')

# Remove the top and right spines (borders)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Optionally, if you want just thin lines on the bottom/left:
ax.spines['bottom'].set_linewidth(0.8)
ax.spines['left'].set_linewidth(0.8)

# Label
ax.set_ylabel('Cost per Flag ($)')

# Annotate bars with values
for bar in bars:
    height = bar.get_height()
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        height + 0.005,
        f"{height:.2f}",
        ha='center',
        va='bottom'
    )

plt.tight_layout()
fig.savefig('cost_per_flag.svg', format='svg')



# Query to get max flags submitted per run
flag_query = """
SELECT
  run_id,
  MAX(
    CAST(
      SUBSTR(
        result_text,
        INSTR(result_text, '(') + 1,
        INSTR(result_text, '/') - INSTR(result_text, '(') - 1
      ) AS INTEGER
    )
  ) AS max_flag_submitted
FROM tool_calls
WHERE
  function_name = 'SubmitFlag'
  AND result_text LIKE 'Flag submitted%'
GROUP BY run_id;
"""

# Query to get all runs from messages
run_query = "SELECT DISTINCT run_id FROM messages;"

# Build combined DataFrame including zero-flag runs
df_list = []
for source, path in db_info.items():
    conn = sqlite3.connect(path)
    runs_df = pd.read_sql_query(run_query, conn)
    flags_df = pd.read_sql_query(flag_query, conn)
    conn.close()

    # Include runs with no flag submissions
    merged = runs_df.merge(flags_df, on='run_id', how='left')
    merged['max_flag_submitted'] = merged['max_flag_submitted'].fillna(0).astype(int)
    merged['source'] = source
    df_list.append(merged)

combined_df = pd.concat(df_list, ignore_index=True)

# Prepare data for violin plot
data = [combined_df[combined_df['source'] == src]['max_flag_submitted'] for src in db_info.keys()]

# Create violin plot with multi-line x-axis labels
fig, ax = plt.subplots()
ax.violinplot(data, showmedians=True)
ax.set_ylabel('Max Flags Submitted')

# Multi-line tick labels with updated source names
labels = [
    'openai\ngpt-4.1-2025-04-14',
    'google\ngemini-2.5-flash-preview-05-20',  # renamed first line
    'meta\nllama-4-maverick-17b-128e-instruct'
]
ax.set_xticks([1, 2, 3])
ax.set_xticklabels(labels)

# Final layout adjustments
plt.tight_layout()
fig.savefig('violins.svg', format='svg')

data = [combined_df[combined_df['source'] == src]['max_flag_submitted'] for src in db_info.keys()]

# Create violin plot
fig, ax = plt.subplots(figsize=(6.4, 4))  # you can tweak figsize as desired
parts = ax.violinplot(data, showmedians=True)

# Style the violins: fill orange, thin black edge
for pc in parts['bodies']:
    pc.set_facecolor('orange')
    #pc.set_edgecolor('black')
    pc.set_alpha(0.8)
# Style the median lines
parts['cmedians'].set_color('black')
parts['cmedians'].set_linewidth(1.0)

# Remove top/right spines
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
# Optionally thin the remaining spines
ax.spines['bottom'].set_linewidth(0.8)
ax.spines['left'].set_linewidth(0.8)

# Labels
ax.set_ylabel('Max Flags Submitted')

# Multi-line tick labels with updated source names
labels = [
    'openai\ngpt-4.1-2025-04-14',
    'google\ngemini-2.5-flash\npreview-05-20',
    'meta\nllama-4-maverick\n17b-128e-instruct'
]
ax.set_xticks([1, 2, 3])
ax.set_xticklabels(labels)

plt.tight_layout()
fig.savefig('violins.svg', format='svg')
