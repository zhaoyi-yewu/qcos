#!/bin/bash
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

# Jenkins Docker Container Management Script

set -e

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
cd "${SCRIPT_DIR}"

function usage {
    echo "Usage: $0 [OPTION]"
    echo "Start or manage Jenkins Docker container"
    echo ""
    echo "  -s, --start       Start Jenkins container (default)"
    echo "  -d, --stop        Stop Jenkins container"
    echo "  -r, --restart     Restart Jenkins container"
    echo "  -l, --logs        View Jenkins logs"
    echo "  -p, --password    Get initial admin password"
    echo "  -h, --help        Show this help message"
    echo ""
}

ACTION="start"

while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--start)
            ACTION="start"
            shift
            ;;
        -d|--stop)
            ACTION="stop"
            shift
            ;;
        -r|--restart)
            ACTION="restart"
            shift
            ;;
        -l|--logs)
            ACTION="logs"
            shift
            ;;
        -p|--password)
            ACTION="password"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

case $ACTION in
    start)
        echo ">>> Starting Jenkins container..."
        docker-compose up -d
        echo ">>> Jenkins started!"
        echo ">>> Access URL: http://localhost:8080"
        echo ">>> To get initial password, run: $0 --password"
        ;;
    stop)
        echo ">>> Stopping Jenkins container..."
        docker-compose down
        echo ">>> Jenkins stopped"
        ;;
    restart)
        echo ">>> Restarting Jenkins container..."
        docker-compose restart
        echo ">>> Jenkins restarted"
        ;;
    logs)
        echo ">>> Jenkins logs (Ctrl+C to exit):"
        docker-compose logs -f
        ;;
    password)
        echo ">>> Getting Jenkins initial admin password..."
        if docker exec jenkins_cicd cat /var/jenkins_home/secrets/initialAdminPassword 2>/dev/null; then
            echo ""
        else
            echo ">>> Password file not found (initialization may be complete)"
        fi
        ;;
esac