"""Output scoring engine — evaluates prompts against the Cyan Black review rubric."""

RUBRIC = {
    'canon_fidelity': {
        'label': 'Canon Fidelity',
        'description': 'Does the output obey locked world rules and character definitions?',
        'weight': 0.25,
    },
    'character_accuracy': {
        'label': 'Character Accuracy',
        'description': 'Are character appearances, clothing, and silhouettes correct?',
        'weight': 0.25,
    },
    'visual_clarity': {
        'label': 'Visual Clarity / Readability',
        'description': 'Is the image readable at intended print or screen size?',
        'weight': 0.20,
    },
    'print_impact': {
        'label': 'Print Impact',
        'description': 'Does the image hold up at print resolution with strong composition?',
        'weight': 0.15,
    },
    'mood_alignment': {
        'label': 'Mood Alignment',
        'description': 'Does the mood match the intended story beat or scene intent?',
        'weight': 0.15,
    },
}


class ReviewEngine:
    def interactive_review(self, entry: dict) -> dict:
        print(f"\n╔══════════════════════════════════════╗")
        print(f"║       OUTPUT REVIEW — RUBRIC          ║")
        print(f"╚══════════════════════════════════════╝\n")
        print(f"Prompt ID: {entry.get('id', 'unknown')}")
        print(f"Type:      {entry.get('type', 'unknown')}")
        print(f"Prompt:    {entry.get('prompt', '')[:100]}...")
        print("\nScore each dimension 0–10 (press Enter to skip):\n")

        scores = {}
        notes = {}

        for key, rubric in RUBRIC.items():
            print(f"── {rubric['label']} (weight: {rubric['weight']:.0%}) ──")
            print(f"   {rubric['description']}")

            while True:
                raw = input("   Score (0–10): ").strip()
                if raw == '':
                    scores[key] = None
                    break
                try:
                    score = float(raw)
                    if 0 <= score <= 10:
                        scores[key] = score
                        note = input("   Note (optional): ").strip()
                        if note:
                            notes[key] = note
                        break
                    else:
                        print("   Enter a number between 0 and 10.")
                except ValueError:
                    print("   Invalid input — enter a number.")
            print()

        overall = self._weighted_average(scores)

        print("── SCORES ───────────────────────────────")
        for key, rubric in RUBRIC.items():
            s = scores.get(key)
            display = f"{s:.1f}" if s is not None else "skipped"
            print(f"   {rubric['label']:<32} {display}")
        print(f"   {'OVERALL (weighted)':<32} {overall:.2f}/10")

        return {
            'dimensions': scores,
            'notes': notes,
            'overall': round(overall, 2),
            'approved': overall >= 7.0,
            'rejected': overall < 5.0,
        }

    def _weighted_average(self, scores: dict) -> float:
        total_weight = 0.0
        weighted_sum = 0.0
        for key, rubric in RUBRIC.items():
            s = scores.get(key)
            if s is not None:
                weighted_sum += s * rubric['weight']
                total_weight += rubric['weight']
        return (weighted_sum / total_weight) if total_weight > 0 else 0.0

    @staticmethod
    def rubric_summary() -> str:
        lines = ["Review Rubric:"]
        for key, r in RUBRIC.items():
            lines.append(f"  {r['label']} ({r['weight']:.0%}): {r['description']}")
        return '\n'.join(lines)
