import re

def extract_code_from_reply(reply):
    match = re.search(r"```python\n(.*?)\n```", reply, re.DOTALL)
    if match:
        return match.group(1).strip()
    return reply

def extract_dbml_from_reply(reply):
    match = re.search(r"```dbml\n(.*?)\n```", reply, re.DOTALL)
    if match:
        return match.group(1).strip()
    return reply

def extract_explanation_from_reply(reply):
    return reply

def extract_filename_from_reply(reply):
    match = re.search(r"filename: (\S+)", reply)
    if match:
        return match.group(1)
    return None

def extract_pytest_from_reply(reply):
    match = re.search(r"```python\n(.*?)\n```", reply, re.DOTALL)
    if match:
        return match.group(1).strip()
    return reply

