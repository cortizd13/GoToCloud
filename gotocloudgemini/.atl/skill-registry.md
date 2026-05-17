# Skill Registry

**Project**: gotocloudgemini
**Generated**: 2026-05-16
**Updated**: 2026-05-16 (SDD Init)

## Project-Level Skills

| Name | Location | Trigger |
|------|----------|---------|
| fastapi-python | .claude/skills/fastapi-python/SKILL.md | FastAPI Python development with async patterns |
| fastapi-templates | .claude/skills/fastapi-templates/SKILL.md | Creating FastAPI projects, async REST APIs |
| python-testing-patterns | .claude/skills/python-testing-patterns/SKILL.md | pytest, TDD, fixtures, mocking, async tests |
| python-executor | .claude/skills/python-executor/SKILL.md | Python sandboxed execution, data processing |

## Global Skills (User-Level)

| Name | Location | Trigger |
|------|----------|---------|
| sdd-init | C:\Users\DELL\.config\opencode/skills/sdd-init/ | SDD initialization |
| sdd-explore | C:\Users\DELL\.config\opencode/skills/sdd-explore/ | SDD exploration |
| sdd-propose | C:\Users\DELL\.config\opencode/skills/sdd-propose/ | SDD proposals |
| sdd-spec | C:\Users\DELL\.config\opencode/skills/sdd-spec/ | SDD specifications |
| sdd-design | C:\Users\DELL\.config\opencode/skills/sdd-design/ | SDD technical design |
| sdd-tasks | C:\Users\DELL\.config\opencode/skills/sdd-tasks/ | SDD task breakdown |
| sdd-apply | C:\Users\DELL\.config\opencode/skills/sdd-apply/ | SDD implementation |
| sdd-verify | C:\Users\DELL\.config\opencode/skills/sdd-verify/ | SDD verification |
| sdd-archive | C:\Users\DELL\.config\opencode/skills/sdd-archive/ | SDD archive |
| sdd-onboard | C:\Users\DELL\.config\opencode/skills/sdd-onboard/ | SDD onboarding |
| branch-pr | C:\Users\DELL\.config\opencode/skills/branch-pr/ | PR creation |
| chained-pr | C:\Users\DELL\.config\opencode/skills/chained-pr/ | Large/stacked PRs |
| cognitive-doc-design | C:\Users\DELL\.config\opencode/skills/cognitive-doc-design/ | Documentation design |
| comment-writer | C:\Users\DELL\.config\opencode/skills/comment-writer/ | Collaboration comments |
| data-agent | C:\Users\DELL\.config\opencode/skills/data-agent/ | Data analysis |
| go-testing | C:\Users\DELL\.config\opencode/skills/go-testing/ | Go tests |
| issue-creation | C:\Users\DELL\.config\opencode/skills/issue-creation/ | GitHub issues |
| judgment-day | C:\Users\DELL\.config\opencode/skills/judgment-day/ | Dual adversarial review |
| skill-creator | C:\Users\DELL\.config\opencode/skills/skill-creator/ | New skills |
| skill-registry | C:\Users\DELL\.config\opencode/skills/skill-registry/ | Registry updates |
| work-unit-commits | C:\Users\DELL\.config\opencode/skills/work-unit-commits/ | Commit splitting |
| find-skills | C:\Users\DELL\.agents/skills/find-skills/ | Skill discovery |

## Project Conventions

- **Convention files**: AGENTS.md (project root), CLAUDE.md (project root)
- **Language**: Python 3.12 with type hints
- **Web framework**: FastAPI (async, WebSocket)
- **AI SDK**: google-genai (Gemini Live API, v1beta)
- **Database**: Supabase (PostgreSQL with RLS)
- **Service language**: Spanish (Colombian) — "Camila" persona
- **Testing**: pytest (testpaths = tests/)
- **Audio**: audioop (stdlib), pyaudio (real-time)
- **Environment**: python-dotenv, `.env` in `backend/`
- **Patterns**: Async concurrency (3-task pattern), Tool-based function dispatch, Singleton Supabase client, Hybrid imports (sys.path + package-relative)
