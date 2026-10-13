# 本地质量验证：数学精确判分 + 生成代码实际执行，输出结果到 logs/verify/
import json, re, sys, time, urllib.request

API = "http://127.0.0.1:8080/v1/chat/completions"

MATH = [
    ("What is 17 * 23? End your reply with a line: ANSWER: <number>", "391"),
    ("What is sqrt(144) + 3^3? End your reply with a line: ANSWER: <number>", "39"),
    ("A shirt costs $80 after a 20% discount. What was the original price in dollars? End your reply with a line: ANSWER: <number>", "100"),
    ("A train travels 150 km in 2.5 hours. What is its average speed in km/h? End your reply with a line: ANSWER: <number>", "60"),
    ("What is 3/4 of 256? End your reply with a line: ANSWER: <number>", "192"),
    ("If 5 machines make 5 widgets in 5 minutes, how many minutes does it take 100 machines to make 100 widgets? End your reply with a line: ANSWER: <number>", "5"),
    ("Solve for x: 3x + 7 = 22. End your reply with a line: ANSWER: <number>", "5"),
    ("A rectangle has perimeter 36 and length 10. What is its width? End your reply with a line: ANSWER: <number>", "8"),
]

CODE = [
    ("""Write a Python function `binary_search(arr, target)` that returns the index of target in sorted list arr, or -1 if absent. Reply with one python code block only.""",
     "assert binary_search([1,3,5,7,9], 7) == 3\nassert binary_search([1,3,5,7,9], 2) == -1\nassert binary_search([], 1) == -1\nassert binary_search([5], 5) == 0"),
    ("""Write a Python function `is_valid_parentheses(s)` that returns True iff s contains a valid bracket sequence using ()[]{}. Reply with one python code block only.""",
     "assert is_valid_parentheses('()[]{}') is True\nassert is_valid_parentheses('([)]') is False\nassert is_valid_parentheses('{[()]}') is True\nassert is_valid_parentheses('') is True"),
    ("""Write a Python function `merge_intervals(intervals)` that merges overlapping [start,end] intervals and returns a sorted list. Reply with one python code block only.""",
     "assert merge_intervals([[1,3],[2,6],[8,10],[15,18]]) == [[1,6],[8,10],[15,18]]\nassert merge_intervals([[1,4],[4,5]]) == [[1,5]]\nassert merge_intervals([]) == []"),
    ("""Write a Python function `roman_to_int(s)` converting a Roman numeral string to an int. Reply with one python code block only.""",
     "assert roman_to_int('III') == 3\nassert roman_to_int('IV') == 4\nassert roman_to_int('LVIII') == 58\nassert roman_to_int('MCMXCIV') == 1994"),
]

def ask(prompt):
    body = json.dumps({
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 1.0, "top_p": 0.95, "top_k": 20, "min_p": 0.05,
        "reasoning_effort": "medium", "max_tokens": 4096,
    }).encode()
    req = urllib.request.Request(API, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.loads(r.read())
    return d["choices"][0]["message"]["content"]

def check_math(reply, expected):
    m = re.findall(r"ANSWER:\s*([-\d.,]+)", reply)
    if not m:
        return False, "no ANSWER line"
    got = m[-1].strip().rstrip(".")
    try:
        ok = float(got.replace(",", "")) == float(expected)
    except ValueError:
        ok = got == expected
    return ok, f"got {got}, want {expected}"

def check_code(reply, tests):
    blocks = re.findall(r"```(?:python)?\n(.*?)```", reply, re.S)
    src = blocks[-1] if blocks else reply
    try:
        env = {}
        exec(src, env)
        exec(tests, env)
        return True, "all asserts passed"
    except AssertionError as e:
        return False, f"assertion failed: {e}"
    except Exception as e:
        return False, f"error: {e}"

def main():
    results, details = [], []
    for i, (q, want) in enumerate(MATH):
        t = time.time()
        reply = ask(q)
        ok, why = check_math(reply, want)
        results.append(ok); details.append((f"math-{i+1}", ok, why, round(time.time()-t,1)))
        print(f"math-{i+1}: {'PASS' if ok else 'FAIL'} ({why}) [{time.time()-t:.0f}s]", flush=True)
    for i, (q, tests) in enumerate(CODE):
        t = time.time()
        reply = ask(q)
        ok, why = check_code(reply, tests)
        results.append(ok); details.append((f"code-{i+1}", ok, why, round(time.time()-t,1)))
        print(f"code-{i+1}: {'PASS' if ok else 'FAIL'} ({why}) [{time.time()-t:.0f}s]", flush=True)
    passed = sum(results)
    print(f"\nTOTAL: {passed}/{len(results)} = {passed/len(results)*100:.0f}%")
    with open("logs/verify/results.json", "w", encoding="utf-8") as f:
        json.dump({"total": len(results), "passed": passed,
                   "items": [{"id": n, "pass": o, "detail": w, "seconds": s} for n, o, w, s in details]},
                  f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
