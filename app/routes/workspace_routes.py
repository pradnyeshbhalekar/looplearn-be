import json
from flask import Blueprint, request, jsonify
from app.services.workspace_service import (
    create_workspace, 
    add_workspace_member, 
    remove_workspace_member, 
    get_user_workspaces, 
    get_workspace_members, 
    delete_workspace
)
from     app.config.db import get_connection
from app.utils.auth_decorators import require_auth

bp = Blueprint("workspaces", __name__)

@bp.route("/", methods=["POST"])
@require_auth
def api_create_workspace(user):
    data = request.json
    name = data.get("name")
    owner_id = user["user_id"]
    seat_limit = data.get("seat_limit", 5)

    if not name:
        return jsonify({"error": "Missing required fields: name"}), 400

    workspace_id = create_workspace(name, owner_id, seat_limit)
    return jsonify({"message": "Workspace created successfully", "workspace_id": workspace_id}), 201

@bp.route("/", methods=["GET"])
@require_auth
def api_get_user_workspaces(user):
    user_id = user["user_id"]
    workspaces = get_user_workspaces(user_id)
    return jsonify({"workspaces": workspaces}), 200

@bp.route("/<workspace_id>", methods=["GET"])
@require_auth
def api_get_workspace_details(user, workspace_id):
    members = get_workspace_members(workspace_id)
    return jsonify({"members": members}), 200

@bp.route("/<workspace_id>/members", methods=["POST"])
@require_auth
def api_add_workspace_member(user, workspace_id):
    data = request.json
    email = data.get("email")
    role = data.get("role", "member")
    
    if not email:
        return jsonify({"error": "Missing email"}), 400

    # Look up user by email
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE email = %s", (email,))
    user = c.fetchone()
    
    if not user:
        return jsonify({"error": "User with this email not found"}), 404
        
    user_id = user[0]
    
    add_workspace_member(workspace_id, user_id, role)
    return jsonify({"message": f"Added user to workspace as {role}"}), 200

@bp.route("/<workspace_id>/members/<user_id>", methods=["DELETE"])
@require_auth
def api_remove_workspace_member(user, workspace_id, user_id):
    # TODO: Verify requesting user is admin of workspace
    remove_workspace_member(workspace_id, user_id)
    return jsonify({"message": "Member removed"}), 200

@bp.route("/<workspace_id>", methods=["DELETE"])
@require_auth
def api_delete_workspace(user, workspace_id):
    # TODO: Verify requesting user is admin
    delete_workspace(workspace_id)
    return jsonify({"message": "Workspace deleted"}), 200

