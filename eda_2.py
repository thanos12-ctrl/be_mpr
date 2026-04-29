import pandas as pd
import matplotlib.pyplot as plt

# HD settings (important for report)
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300

# Load dataset
df = pd.read_csv("Data/questions.csv")

# ================================
# Create Summary Table
# ================================
summary = df.groupby('part').agg(
    Bundles=('bundle_id', 'nunique'),
    Questions=('question_id', 'count')
).reset_index()

summary['Avg_Q_per_Bundle'] = summary['Questions'] / summary['Bundles']

# Sort properly
summary = summary.sort_values('part')

# ================================
# 1. PIE CHART (HD)
# ================================
plt.figure(figsize=(10, 8))

plt.pie(
    summary['Questions'],
    labels=[f'Part {int(p)}' for p in summary['part']],
    autopct='%1.1f%%',
    startangle=90
)

plt.title("Questions Distribution Across Parts", fontsize=16)

plt.tight_layout()
plt.savefig("questions_distribution_hd.png")
plt.show()


# ================================
# 2. TABLE (HD)
# ================================
fig, ax = plt.subplots(figsize=(12, 4))
ax.axis('off')

summary_display = summary.copy()
summary_display['Avg_Q_per_Bundle'] = summary_display['Avg_Q_per_Bundle'].round(1)

table = ax.table(
    cellText=summary_display.values,
    colLabels=["Part", "Bundles", "Questions", "Avg Q/Bundle"],
    cellLoc='center',
    loc='center'
)

# Styling
table.auto_set_font_size(False)
table.set_fontsize(12)
table.scale(1, 2)

for (row, col), cell in table.get_celld().items():
    if row == 0:
        cell.set_facecolor('#4CAF50')
        cell.set_text_props(color='white', weight='bold')
    else:
        cell.set_facecolor('#F5F5F5')

plt.title("EdNet Dataset Summary", fontsize=16)

plt.savefig("ednet_table_hd.png", bbox_inches='tight')
plt.show()