# Local GitLab Server Integration (bot0004)

The local GitLab server is accessible from both the host browser and this container:
- **Host Browser Link (Open on Host):** http://localhost:8929/dashboard (or http://192.168.0.3:8929/dashboard)
- **Host Personal Project Link:** http://localhost:8929/bot0004/personal (or http://192.168.0.3:8929/bot0004/personal)
- **Container GitLab Server URL:** http://192.168.0.3:8929
- **Container Direct IP:** http://192.168.0.3:8929
- **Central Project:** http://192.168.0.3:8929/georgydunaev/mybot.git
- **Your Personal Project:** http://192.168.0.3:8929/bot0004/personal.git
- **API v4 Base:** http://192.168.0.3:8929/api/v4/projects
- **Personal Access Token:** glpat-aibotssecrettoken123

### Available Tools:
- `/app/gitlab-cli status` — test connection
- `/app/gitlab-cli issue create --title "..." --description "..."` — create issue
- `/app/gitlab-cli mr create --source <branch> --title "..."` — submit merge request
- `/app/git-local-gitlab.sh push` — push workspace commits to GitLab
- `./mybot/forhost.sh` — print and bridge host browser URLs
