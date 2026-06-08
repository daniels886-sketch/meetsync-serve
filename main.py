from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import json

app = Flask(__name__)
CORS(app)  # Allow requests from the iPhone app

MONDAY_API_URL = "https://api.monday.com/v2"
MONDAY_TOKEN = os.environ.get("MONDAY_TOKEN", "")

def monday_request(query, variables=None):
    headers = {
        "Authorization": MONDAY_TOKEN,
        "Content-Type": "application/json",
        "API-Version": "2024-01"
    }
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    r = requests.post(MONDAY_API_URL, json=payload, headers=headers)
    return r.json()

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "MeetSync"})

@app.route("/send-tasks", methods=["POST"])
def send_tasks():
    data = request.get_json()
    if not data or "items" not in data:
        return jsonify({"error": "No items provided"}), 400

    results = []
    errors = []

    for item in data["items"]:
        try:
            name        = item.get("name", "")
            board_id    = item.get("boardId", 5018502514)
            group_id    = item.get("groupId", "new_group35361__1")
            status      = item.get("status", "עוד לא התחיל")
            priority    = item.get("priority", "Medium")
            date        = item.get("date", "")
            person_id   = item.get("personId", 89872068)
            placement   = item.get("placement", "new")
            parent_id   = item.get("parentId")
            notes       = item.get("notes", "")

            # Map priority label to Monday column id
            priority_map = {
                "Critical ⚠️": "Critical ⚠️️",
                "High": "High",
                "Medium": "Medium",
                "Low": "Low"
            }
            priority_label = priority_map.get(priority, "Medium")

            col_values = {
                "status2__1": {"label": status},
                "color_mkv5n2xp": {"label": priority_label},
                "people__1": {"personsAndTeams": [{"id": person_id, "kind": "person"}]},
                "date0__1": {"date": date} if date else {}
            }
            col_values_str = json.dumps(col_values)

            if placement == "sub" and parent_id:
                # Create as subitem
                query = """
                mutation ($parent_id: ID!, $name: String!) {
                  create_subitem (parent_item_id: $parent_id, item_name: $name) {
                    id
                    name
                  }
                }
                """
                variables = {
                    "parent_id": str(parent_id),
                    "name": name
                }
                resp = monday_request(query, variables)
                item_id = resp.get("data", {}).get("create_subitem", {}).get("id")
            else:
                # Create as new item
                query = """
                mutation ($board_id: ID!, $group_id: String!, $name: String!, $col_vals: JSON!) {
                  create_item (
                    board_id: $board_id,
                    group_id: $group_id,
                    item_name: $name,
                    column_values: $col_vals
                  ) {
                    id
                    name
                  }
                }
                """
                variables = {
                    "board_id": str(board_id),
                    "group_id": group_id,
                    "name": name,
                    "col_vals": col_values_str
                }
                resp = monday_request(query, variables)
                item_data = resp.get("data", {}).get("create_item", {})
                item_id = item_data.get("id")

            if item_id:
                # Add notes as update if provided
                if notes:
                    update_query = """
                    mutation ($item_id: ID!, $body: String!) {
                      create_update (item_id: $item_id, body: $body) { id }
                    }
                    """
                    monday_request(update_query, {"item_id": str(item_id), "body": notes})

                results.append({"name": name, "id": item_id, "status": "created"})
            else:
                errors.append({"name": name, "error": str(resp)})

        except Exception as e:
            errors.append({"name": item.get("name", "?"), "error": str(e)})

    return jsonify({
        "success": len(results),
        "errors": len(errors),
        "results": results,
        "error_details": errors
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
