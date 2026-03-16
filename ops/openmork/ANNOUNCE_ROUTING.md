# Announce routing (domain/category)

Config file (YAML or JSON): `~/.openmork/announce_routing.yaml`

Priority order:
1. `routes.domain.<domain>`
2. `routes.category.<category>`
3. `routes.default`
4. fallback target passed by caller (normally platform home channel)

Example:
```yaml
routes:
  domain:
    design: "discord:#design"
    marketing: "telegram:-1001234567890"
  category:
    incident: "telegram:-1009999999999"
  default: "telegram"
```

Use case:
- design -> canal A
- marketing -> canal B
- default -> home channel
