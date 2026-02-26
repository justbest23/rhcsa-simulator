"""
Domain 9: Container Management
Categories: containers
"""

CONTENT = {
    "containers": {
        "name": "Container Management (Podman)",
        "explanation": """
Podman is the container engine in RHEL 8/9, compatible with Docker commands.
You must know how to run containers, manage images, configure port mapping,
set environment variables, and make containers persistent with systemd.
The exam tests basic podman commands: run, ps, images, exec, and creating
systemd unit files for rootless containers.
        """,
        "commands": [
            {
                "name": "Run Container",
                "syntax": "podman run -d --name <name> -p <host>:<container> <image>",
                "example": "podman run -d --name web -p 8080:80 nginx",
                "flags": {
                    "-d": "Detached mode (background)",
                    "--name": "Container name",
                    "-p": "Port mapping (host:container)",
                    "-e": "Environment variable",
                    "-v": "Volume mount (host:container)",
                },
            },
            {
                "name": "List Containers",
                "syntax": "podman ps -a",
                "example": "podman ps -a",
                "flags": {
                    "ps": "List running containers",
                    "-a": "Show all (including stopped)",
                    "ps -l": "Show latest container",
                },
            },
            {
                "name": "List Images",
                "syntax": "podman images",
                "example": "podman images",
                "flags": {
                    "images": "List all local images",
                    "pull <image>": "Download image",
                    "rmi <image>": "Remove image",
                },
            },
            {
                "name": "Execute in Container",
                "syntax": "podman exec -it <container> <command>",
                "example": "podman exec -it web /bin/bash",
                "flags": {
                    "exec": "Run command in running container",
                    "-it": "Interactive terminal",
                    "logs <container>": "View container logs",
                },
            },
            {
                "name": "Generate Systemd Unit",
                "syntax": "podman generate systemd --name <container> --files --new",
                "example": "podman generate systemd --name web --files --new",
                "flags": {
                    "generate systemd": "Create systemd unit file",
                    "--name": "Use container name",
                    "--files": "Write to file",
                    "--new": "Create new container on start",
                    "systemctl --user": "User service (rootless)",
                },
            },
        ],
        "common_mistakes": [
            "Forgetting -d flag (container runs in foreground)",
            "Port already in use on host",
            "Not pulling image before running",
            "Wrong systemd path for user services",
            "Forgetting to enable systemd service",
        ],
        "exam_tricks": [
            "Rootless containers use systemctl --user",
            "User systemd units go in ~/.config/systemd/user/",
            "Must enable AND start systemd service",
            "Container name must match in systemd commands",
        ],
    },
}
