# Audit Code Health Skill

A Claude skill for analyzing codebase health and providing actionable recommendations for improving code quality, maintainability, and technical debt.

## Installation

Install this skill using the Skills CLI:

```bash
npx skills add https://github.com/kyzooghost/audit-code-health-skill --skill audit-code-health
```

## Usage

Once installed, use the skill in Claude Code:

```bash
For @folder do /audit-code-health
```

The skill will analyze your codebase and provide a comprehensive health report with prioritized recommendations.

## What This Skill Does

This skill helps you:

- **Assess Code Quality** - Evaluate code health metrics and identify problem areas
- **Identify Technical Debt** - Find areas that need refactoring or improvement
- **Prioritize Improvements** - Get actionable recommendations ranked by impact
- **Track Progress** - Monitor codebase health over time
- **Make Informed Decisions** - Use data-driven insights for planning refactoring efforts

## Repository Structure

```
audit-code-health-skill/
├── SKILL.md              # Complete skill documentation and implementation
├── README.md            # This file
├── references/          # Supporting documentation and resources
└── metadata.json        # Additional skill metadata
```

## Development

### Testing Locally

1. Clone this repository
2. Make your changes to `SKILL.md`
3. Test locally:
   ```bash
   npx skills add .
   ```
4. Verify the skill appears in Claude Code:
   ```bash
   /skills
   ```

### Populating Skill Content

The `SKILL.md` file contains a template with placeholder content. To complete the skill:

1. Replace placeholder sections with your actual implementation
2. Add specific workflows, examples, and guidelines
3. Include reference documentation in the `references/` directory
4. Update metadata in both `SKILL.md` frontmatter and `metadata.json`

Reference the existing [code-health-auditor skill](https://github.com/vercel-labs/skills) for examples.

## Verification

After installation, verify the skill works correctly:

```bash
# In Claude Code, list all skills
/skills

# Use the skill
/audit-code-health

# Check skill metadata
npx skills list
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally using `npx skills add .`
5. Submit a pull request

## License

MIT

## Resources

- [Agent Skills Specification](https://agentskills.io/specification)
- [Skills Repository](https://github.com/vercel-labs/skills)
- [Claude Code Documentation](https://claude.ai/code)

## Support

For issues or questions:
- Open an issue in this repository
- Refer to the [Skills CLI documentation](https://github.com/vercel-labs/skills)
- Check the [Agent Skills specification](https://agentskills.io/specification)
