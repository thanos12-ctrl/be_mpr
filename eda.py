import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from collections import Counter

def visualize_ednet_structure(questions_csv_path='Data/questions.csv'):
    """
    Visualization of EdNet data structure:
    - Pie chart: Questions distribution across parts (solo figure)
    - Stats table: Detailed part statistics (solo figure)
    """

    # Load questions data
    print("Loading questions.csv...")
    df = pd.read_csv(questions_csv_path)

    print(f"Total questions: {len(df)}")
    print(f"Columns: {list(df.columns)}")

    # Set style
    plt.style.use('seaborn-v0_8-darkgrid')
    sns.set_palette("husl")

    # ============================================================================
    # OVERALL STATISTICS
    # ============================================================================

    total_questions = len(df)
    total_bundles = df['bundle_id'].nunique()
    total_parts = df['part'].nunique()

    print("\n" + "="*60)
    print("EDNET DATA STRUCTURE SUMMARY")
    print("="*60)
    print(f"Total Questions: {total_questions:,}")
    print(f"Total Bundles: {total_bundles:,}")
    print(f"Total Parts (Chapters): {total_parts}")
    print(f"Avg Questions per Bundle: {total_questions/total_bundles:.1f}")
    print(f"Avg Bundles per Part: {total_bundles/total_parts:.1f}")
    print("="*60)

    questions_per_part = df.groupby('part').size()

    # ============================================================================
    # FIGURE 1: PIE CHART — Questions Distribution Across Parts
    # ============================================================================

    fig1, ax6 = plt.subplots(figsize=(8, 8))

    colors = plt.cm.Set3(np.linspace(0, 1, len(questions_per_part)))
    wedges, texts, autotexts = ax6.pie(
        questions_per_part,
        labels=[f'Part {p}' for p in questions_per_part.index],
        autopct='%1.1f%%',
        colors=colors,
        startangle=90,
        textprops={'fontsize': 14, 'fontweight': 'bold'}
    )

    ax6.set_title('Questions Distribution Across Parts', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig('ednet_pie_chart.png', dpi=300, bbox_inches='tight')
    print("\n✓ Pie chart saved as 'ednet_pie_chart.png'")
    plt.show()

    # ============================================================================
    # FIGURE 2: DETAILED STATISTICS TABLE
    # ============================================================================

    fig2, ax8 = plt.subplots(figsize=(7, 5))
    ax8.axis('tight')
    ax8.axis('off')

    # Prepare statistics table
    stats_data = []
    for part in sorted(df['part'].unique()):
        part_df = df[df['part'] == part]
        n_bundles = part_df['bundle_id'].nunique()
        n_questions = len(part_df)
        avg_q_per_bundle = n_questions / n_bundles if n_bundles > 0 else 0

        stats_data.append([
            f'Part {part}',
            f'{n_bundles}',
            f'{n_questions}',
            f'{avg_q_per_bundle:.1f}'
        ])

    table = ax8.table(
        cellText=stats_data,
        colLabels=['Part', 'Bundles', 'Questions', 'Avg Q/Bundle'],
        cellLoc='center',
        loc='center',
        colWidths=[0.2, 0.2, 0.2, 0.3]
    )

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)

    # Style header
    for i in range(4):
        table[(0, i)].set_facecolor('#4CAF50')
        table[(0, i)].set_text_props(weight='bold', color='white')

    # Alternate row colors
    for i in range(1, len(stats_data) + 1):
        for j in range(4):
            if i % 2 == 0:
                table[(i, j)].set_facecolor('#f0f0f0')

    ax8.set_title('Detailed Part Statistics', fontsize=14, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.savefig('ednet_stats_table.png', dpi=300, bbox_inches='tight')
    print("✓ Stats table saved as 'ednet_stats_table.png'")
    plt.show()

    return df, questions_per_part


def create_hierarchy_visualization(questions_csv_path='questions.csv'):
    """
    Create a hierarchical tree visualization showing Part → Bundle → Questions
    """
    df = pd.read_csv(questions_csv_path)

    fig, ax = plt.subplots(figsize=(16, 10))

    parts = sorted(df['part'].unique())

    y_position = 0
    spacing = 2

    for part_idx, part in enumerate(parts):
        part_df = df[df['part'] == part]
        bundles = part_df['bundle_id'].unique()[:5]  # Show first 5 bundles per part

        part_y = y_position + len(bundles) * spacing / 2
        ax.scatter([0], [part_y], s=1000, c='red', alpha=0.7, zorder=3)
        ax.text(0, part_y, f'Part {part}', ha='center', va='center',
                fontweight='bold', fontsize=10, color='white')

        for bundle_idx, bundle in enumerate(bundles):
            bundle_y = y_position + bundle_idx * spacing
            n_questions = len(part_df[part_df['bundle_id'] == bundle])

            ax.scatter([2], [bundle_y], s=800, c='blue', alpha=0.6, zorder=3)
            ax.text(2, bundle_y, f'Bundle\n{bundle}\n({n_questions}Q)',
                   ha='center', va='center', fontsize=8, fontweight='bold')

            ax.plot([0, 2], [part_y, bundle_y], 'k-', alpha=0.3, linewidth=1)

            for q_idx in range(min(3, n_questions)):
                q_y = bundle_y + (q_idx - 1) * 0.3
                ax.scatter([4], [q_y], s=200, c='green', alpha=0.5, zorder=2)
                ax.text(4.3, q_y, f'Q', ha='left', va='center', fontsize=7)
                ax.plot([2, 4], [bundle_y, q_y], 'k-', alpha=0.2, linewidth=0.5)

        y_position += len(bundles) * spacing + 2

    ax.set_xlim(-1, 5)
    ax.set_ylim(-2, y_position)
    ax.axis('off')
    ax.set_title('EdNet Hierarchy: Part → Bundle → Questions (Sample)',
                 fontsize=16, fontweight='bold', pad=20)

    ax.scatter([], [], s=1000, c='red', alpha=0.7, label='Part (Chapter)')
    ax.scatter([], [], s=800, c='blue', alpha=0.6, label='Bundle')
    ax.scatter([], [], s=200, c='green', alpha=0.5, label='Question')
    ax.legend(loc='upper right', fontsize=12)

    plt.tight_layout()
    plt.savefig('ednet_hierarchy.png', dpi=300, bbox_inches='tight')
    print("✓ Hierarchy visualization saved as 'ednet_hierarchy.png'")
    plt.show()


# Main execution
if __name__ == "__main__":
    print("EdNet Dataset Structure Visualization")
    print("=" * 60)

    df, q_per_part = visualize_ednet_structure('Data/questions.csv')

    print("\nCreating hierarchy visualization...")
    create_hierarchy_visualization('questions.csv')

    print("\n✓ All visualizations complete!")
    print("\nGenerated files:")
    print("  - ednet_pie_chart.png (questions distribution pie chart)")
    print("  - ednet_stats_table.png (detailed part statistics table)")
    print("  - ednet_hierarchy.png (tree structure)")