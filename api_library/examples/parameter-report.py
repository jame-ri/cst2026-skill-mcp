"""Unverified example. Stage and trial explicitly before registering."""


def run(context, arguments):
    prefix = arguments.get("prefix", "")
    rows = [row for row in context.parameters() if row["name"].startswith(prefix)]
    return {"project_path": context.project_path, "count": len(rows), "parameters": rows}


def verify(context, arguments, result):
    prefix = arguments.get("prefix", "")
    observed = {row["name"]: row["expression"] for row in context.parameters()
                if row["name"].startswith(prefix)}
    returned = {row["name"]: row["expression"] for row in result["parameters"]}
    passed = observed == returned and result["count"] == len(observed)
    return {"passed": passed, "summary": "Compared returned expressions with a second live CST read.",
            "evidence": {"parameter_count": len(observed), "expressions_match": observed == returned,
                         "project_path": context.project_path}}
