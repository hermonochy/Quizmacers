from fractions import Fraction
import re


def _answers(correct, nearby):
    options = [str(correct)]
    for value in nearby:
        value = str(value)
        if value not in options:
            options.append(value)
        if len(options) == 4:
            break
    if len(options) < 4:
        parsed = re.fullmatch(r'(-?\d+)(.*)', str(correct))
        if parsed is None:
            raise ValueError(f'Not enough distinct answer choices for {correct}')
        base, suffix = int(parsed.group(1)), parsed.group(2)
        offset = 1
        while len(options) < 4:
            for candidate in (base + offset, base - offset):
                alternative = f'{candidate}{suffix}'
                if alternative not in options:
                    options.append(alternative)
                    if len(options) == 4:
                        break
            offset += 1
    return tuple(options)


def _linear(a, b, solution):
    value = a * solution + b
    sign = f'+ {b}' if b >= 0 else f'- {-b}'
    return f'Solve {a}x {sign} = {value}.', _answers(solution, (solution + 1, solution - 1, -solution, solution + 2))


def _quadratic(first, second):
    sum_ = first + second
    product = first * second
    middle = -sum_
    mid = f'+ {middle}x' if middle >= 0 else f'- {-middle}x'
    last = f'+ {product}' if product >= 0 else f'- {-product}'
    prompt = f'Solve x^2 {mid} {last} = 0.'
    def pair(x, y):
        a, b = sorted((x, y))
        return f'x = {a} or {b}'
    correct = pair(first, second)
    other = (pair(-first, -second), pair(first + 1, second + 1),
             pair(first - 1, second + 1), pair(first + 2, second - 1),
             pair(-first, second), pair(first, -second))
    return prompt, _answers(correct, other)


def _binomial(a, b):
    middle = a + b
    const = a * b
    def expression(mid, value):
        m = f'+ {mid}x' if mid >= 0 else f'- {-mid}x'
        k = f'+ {value}' if value >= 0 else f'- {-value}'
        return f'x^2 {m} {k}'
    correct = expression(middle, const)
    choice = _answers(correct, (expression(a - b, const), expression(middle, -const),
                               expression(middle + 1, const), expression(middle, const + 1)))
    left = f'(x + {a})' if a >= 0 else f'(x - {-a})'
    right = f'(x + {b})' if b >= 0 else f'(x - {-b})'
    return f'Expand {left}{right}.', choice


def make_expanded_maths():
    records = []

    def add(course, subtopic, prompt, options, seconds=None):
        assert len(options) == len(set(options)) == 4, (prompt, options)
        records.append((course, subtopic, prompt, *options, seconds))

    for total in (10, 20):
        for left in range(3, total, 2):
            right = total - left
            add('KS1', 'Number Bonds', f'Complete {left} + ? = {total}.',
                _answers(right, (right + 1, right - 1, left, right + 2)), 15)
    for tens in range(2, 9):
        for ones in (1, 3, 5, 7):
            answer = 10 * tens + ones
            add('KS1', 'Place Value', f'What number has {tens} tens and {ones} ones?',
                _answers(answer, (tens + ones, ones * 10 + tens, answer + 10, answer - 1)), 18)
    for a in range(12, 38, 3):
        for b in (4, 8):
            add('KS1', 'Adding and Subtracting', f'Calculate {a} + {b}.',
                _answers(a + b, (a + b + 1, a + b - 1, a - b)), 20)
            add('KS1', 'Adding and Subtracting', f'Calculate {a + b} - {b}.',
                _answers(a, (a + 1, a - 1, a + b)), 20)
    for length in (2, 4, 6, 8, 10):
        add('KS1', 'Shapes and Measures', f'Join ribbons of {length} cm and {length+3} cm. Total?',
            _answers(f'{2 * length+3} cm', (f'{length+3} cm', f'{length*2} cm', f'{2 * length+4} cm')), 24)

    for denominator in (2, 3, 4, 5, 6, 8):
        for factor in (4, 6, 8, 10):
            amount = factor * denominator
            add('KS2 (SATs)', 'Fractions', f'What is 1/{denominator} of {amount}?',
                _answers(factor, (amount - factor, factor + denominator, denominator)), 29)
    for percent in (10, 20, 25, 50, 75):
        for number in (40, 80, 120, 200, 240):
            result = number * percent // 100
            add('KS2 (SATs)', 'Decimals and Percentages', f'Find {percent}% of {number}.',
                _answers(result, (number // 10, result + 10, result * 2, number - result)), 35)
    for width in (3, 5, 7, 9):
        for height in (4, 6, 8, 10):
            add('KS2 (SATs)', 'Geometry', f'Find the area of a {width} cm by {height} cm rectangle.',
                _answers(f'{width * height} cm^2', (f'{2*(width+height)} cm^2', f'{width+height} cm^2', f'{width * height * 2} cm^2')), 34)
    for metres in (2, 3, 4, 6, 8, 12):
        add('KS2 (SATs)', 'Measurement', f'Convert {metres} m to centimetres.',
            _answers(f'{100 * metres} cm', (f'{10 * metres} cm', f'{1000 * metres} cm', f'{metres} cm')), 22)
    for number in (1346, 2678, 3912, 4771, 5284, 6458, 7319, 8643, 9721):
        rounded = ((number + 50) // 100) * 100
        add('KS2 (SATs)', 'Place Value', f'Round {number} to the nearest hundred.',
            _answers(rounded, (rounded - 100, rounded + 100, number // 100 * 100 + 50)), 28)

    for solution in (-5, -3, 2, 4, 6, 8):
        for a, b in ((2, 3), (3, -4), (4, 5), (5, -7)):
            prompt, options = _linear(a, b, solution)
            add('KS3', 'Algebra', prompt, options, 40)
    for a in (2, 3, 4, 5):
        for b in (3, 5, 7):
            add('KS3', 'Algebra', f'Expand {a}(x + {b}).',
                (f'{a}x + {a*b}', f'{a}x + {b}', f'{a+b}x', f'x + {a*b}'), 36)
    for first, second in ((2, 3), (3, 4), (3, 5), (4, 7), (5, 6)):
        for multiple in (3, 5, 7):
            total = (first + second) * multiple
            add('KS3', 'Fractions and Ratios', f'Split {total} in ratio {first}:{second}. Smaller share?',
                _answers(min(first, second)*multiple, (max(first, second)*multiple, total // 2, first + second)), 49)
    for base in range(4, 15):
        add('KS3', 'Number', f'Calculate {base} squared.',
            _answers(base**2, (base * 2, base**2 + 2, base**2 - 2)), 27)
    for base, height in ((5, 6), (8, 7), (10, 9), (12, 5), (14, 8)):
        add('KS3', 'Geometry', f'Area of triangle: base {base} cm, height {height} cm?',
            _answers(f'{base*height//2} cm^2', (f'{base*height} cm^2', f'{base+height} cm^2', f'{base*height//2+5} cm^2')), 42)
    for a, b in ((4, 8), (6, 12), (10, 14), (7, 15), (8, 16)):
        for c in (6, 12):
            total = a + b + c
            if total % 3 == 0:
                add('KS3', 'Probability and Statistics', f'Mean of {a}, {b}, {c}?',
                    _answers(total // 3, (total // 3 + 1, total // 3 - 1, max(a, b, c))), 33)

    roots = ((1, 2), (2, 3), (1, 5), (2, 5), (3, 4), (3, 7), (-1, 2), (-2, 3),
             (-3, 4), (-2, 5), (-4, 1), (-1, -4), (-2, -5), (-3, -6), (4, 6), (5, 7),
             (-4, 5), (-5, 2), (-3, -5), (2, 7), (3, 8), (-2, 7), (6, 9), (-4, 7))
    for course, area in (('GCSE', 'Algebra'), ('IGCSE', 'Algebra and Graphs')):
        for r1, r2 in roots:
            prompt, options = _quadratic(r1, r2)
            add(course, area, prompt, options, 80)
        for a in (-4, -2, 1, 3, 5, 7):
            for b in (-3, -1, 2, 4):
                if a == b:
                    continue
                prompt, options = _binomial(a, b)
                add(course, area, prompt, options, 59)
        for solution in (-3, 2, 5, 8):
            for a, b in ((2, 7), (3, -5), (5, 4)):
                prompt, options = _linear(a, b, solution)
                add(course, area, prompt, options, 40)

    for course, subtopic in (('GCSE', 'Number'), ('IGCSE', 'Number and Sets')):
        for percent in (12, 15, 20, 25, 35):
            for amount in (80, 160, 200, 240):
                value = Fraction(percent * amount, 100)
                if value.denominator == 1:
                    correct = value.numerator
                    add(course, subtopic, f'Calculate {percent}% of {amount}.',
                        _answers(correct, (correct + 10, correct - 10, amount - correct)), 41)
    for course, subtopic in (('GCSE', 'Geometry'), ('IGCSE', 'Geometry and Trigonometry')):
        for a, b, c in ((3,4,5), (5,12,13), (8,15,17), (7,24,25), (9,40,41), (12,35,37)):
            add(course, subtopic, f'Right triangle legs {a} cm, {b} cm. Hypotenuse?',
                _answers(f'{c} cm', (f'{a+b} cm', f'{c-2} cm', f'{c+2} cm')), 55)
    for course, subtopic in (('GCSE', 'Probability and Statistics'), ('IGCSE', 'Statistics and Probability')):
        for first, second in ((1,5), (2,6), (3,7), (4,8), (5,9), (6,10), (7,11)):
            mean = (first + second) // 2
            add(course, subtopic, f'Mean of {first}, {second}, {mean}?',
                _answers(mean, (mean - 1, mean + 1, first + second)), 33)
    for a, b in ((2,3), (3,4), (4,5), (5,7), (6,11), (7,13), (8,15)):
        for multiplier in (5, 8, 12):
            total = (a+b)*multiplier
            add('GCSE', 'Ratio and Proportion', f'Share {total} in ratio {a}:{b}. Larger share?',
                _answers(max(a,b)*multiplier, (min(a,b)*multiplier, total // 2, total - multiplier)), 57)

    for power in (2, 3, 4, 5):
        for coefficient in (2, 3, 4, 5, 6, 7):
            add('A level', 'Calculus', f'Differentiate {coefficient}x^{power} with respect to x.',
                _answers(f'{coefficient*power}x^{power-1}',
                         (f'{coefficient}x^{power-1}', f'{coefficient*power}x^{power}', f'{coefficient+power}x^{power-1}')), 60)
    for power in (1, 2, 3, 4):
        for coefficient in (2, 3, 4, 5, 6):
            result = coefficient * (power+1)
            add('A level', 'Calculus', f'Integrate {result}x^{power} with respect to x.',
                _answers(f'{coefficient}x^{power+1} + C',
                         (f'{result}x^{power+1} + C', f'{coefficient}x^{power} + C',
                          f'{coefficient*power}x^{power+1} + C')), 73)
    for r1, r2 in roots[:18]:
        sum_ = r1 + r2
        prod = r1 * r2
        mid = f'+ {-sum_}x' if sum_ < 0 else f'- {sum_}x'
        const = f'+ {prod}' if prod >= 0 else f'- {-prod}'
        add('A level', 'Pure: Algebra', f'Find discriminant of x^2 {mid} {const}.',
            _answers(sum_**2 - 4 * prod,
                     ((sum_**2), (sum_**2 - prod), (sum_**2 + 4*prod))), 58)
    for n, p in ((5, 0.2), (10, 0.3), (12, 0.25), (16, 0.5), (20, 0.1), (30, 0.4)):
        add('A level', 'Statistics', f'For X~Bin({n}, {p}), find E(X).',
            _answers(f'{n*p:g}', (f'{n*(1-p):g}', f'{p:g}', f'{n:g}')), 45)
    for mass in (2, 3, 4, 5, 7):
        for accel in (2, 3, 4):
            force = mass * accel
            add('A level', 'Mechanics', f'Force on {mass} kg with acceleration {accel} m/s^2?',
                _answers(f'{force} N', (f'{mass+accel} N', f'{force+accel} N', f'{mass} N')), 48)
    for angle, sine, cosine in ((0,'0','1'), (30,'1/2','sqrt(3)/2'), (45,'sqrt(2)/2','sqrt(2)/2'),
                                (60,'sqrt(3)/2','1/2'), (90,'1','0')):
        alternatives = ('0','1','1/2','sqrt(2)/2','sqrt(3)/2','-1','2')
        for trig, answer in (('sin', sine), ('cos', cosine)):
            add('A level', 'Trigonometry', f'What is {trig}({angle} degrees)?',
                _answers(answer, (value for value in alternatives if value != answer)), 28)
    return tuple(records)


EXPANDED_MATHS = make_expanded_maths()
