def estimate_solve_seconds(course: str, subject: str, subtopic: str, prompt: str) -> float:
    text = prompt.lower()
    area = subtopic.lower()
    if subject.lower() != 'maths' and not subject.lower().startswith('maths::'):
        return 22.0 if len(text) < 85 else 28.0
    if 'quadratic' in text or ('solve' in text and ('x^2' in text or 'x²' in text)):
        return 78.0
    if ('factorise' in text or 'factorize' in text) and ('x^2' in text or 'x²' in text):
        return 65.0
    if 'simultaneous' in text:
        return 95.0
    if 'integrate' in text or 'integration' in text:
        return 73.0
    if 'differentiate' in text or 'derivative' in text:
        return 55.0
    if 'discriminant' in text or 'roots' in text:
        return 58.0
    if 'expand' in text and '(x' in text:
        return 55.0
    if 'rearrange' in text or 'nth term' in text:
        return 60.0
    if 'probability' in text and ('two ' in text or 'three ' in text):
        return 55.0
    if 'ratio' in text or 'proportional' in text:
        return 52.0
    if 'gradient' in text or 'scale factor' in text:
        return 42.0
    if 'solve' in text or 'factorise' in text or 'simplify' in text or 'expand' in text:
        return 48.0 if course in ('GCSE', 'IGCSE', 'A level') else 35.0
    if 'area' in text or 'volume' in text or 'perimeter' in text or 'percent' in text or '%' in text:
        return 42.0 if course in ('GCSE', 'IGCSE', 'A level') else 32.0
    if 'calculus' in area or 'algebra' in area:
        return 38.0 if course in ('GCSE', 'IGCSE', 'A level') else 30.0
    if course == 'A level':
        return 35.0
    return 23.0 if course in ('KS1', 'KS2 (SATs)') else 28.0


def time_limit_for(question) -> float:
    expected = max(3.0, float(question.expected_seconds))
    if getattr(question, 'options', ()):
        return min(180.0, max(30.0, round(expected * 1.62 + 11)))
    return 16.0


def round_length_for(question_seconds: list[float]) -> float:
    if not question_seconds:
        return 210.0
    ordered = sorted(question_seconds)
    typical = ordered[len(ordered) // 2]
    return float(min(540, max(210, 190 + 4.0 * typical)))


def ai_solve_delay(expected: float, difficulty: str, rank_index: int, rng, tier: int = 1) -> float:
    low, high = {
        'Apprentice': (1.18, 1.75),
        'Duelist': (0.94, 1.43),
        'Archmage': (0.71, 1.18),
    }.get(difficulty, (0.94, 1.43))
    rank_multiplier = 1.0 - 0.012 * min(8, rank_index)
    tier_multiplier = 1.0 - 0.025 * max(0, tier - 1)
    return max(1.7, rng.uniform(low, high) * expected * rank_multiplier * tier_multiplier)
