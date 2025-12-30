# Contributing to SceneMachine.ai

Thank you for your interest in contributing to SceneMachine.ai! This document provides guidelines and information for contributors.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## Development Setup

### Prerequisites

- Node.js 20.x or later
- Python 3.11 or later
- Git

### Local Development

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/scenemachine.git
   cd scenemachine
   ```
3. Install dependencies:
   ```bash
   npm install
   cd packages/core && pip install -e ".[dev]" && cd ../..
   ```
4. Create a branch for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Coding Standards

### Python (Backend)

- **Formatter**: Ruff (line length: 100)
- **Linter**: Ruff
- **Type Checker**: mypy (strict mode)
- **Test Framework**: pytest

Run checks:
```bash
cd packages/core
ruff check .
ruff format --check .
mypy .
pytest
```

### TypeScript (Frontend)

- **Formatter**: Prettier
- **Linter**: ESLint
- **Test Framework**: Vitest (unit), Playwright (e2e)

Run checks:
```bash
cd apps/desktop
npm run lint
npm run typecheck
npm test
```

### Commit Messages

Use clear, descriptive commit messages:

```
<type>: <short description>

<optional longer description>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat: add fountain screenplay parser
fix: resolve character consistency in generation
docs: update API documentation for scene endpoints
```

## Pull Request Process

1. **Ensure all tests pass** before submitting
2. **Update documentation** if you're changing APIs or behavior
3. **Fill out the PR template** completely
4. **Link related issues** using GitHub keywords (e.g., "Fixes #123")
5. **Request review** from maintainers

### PR Checklist

- [ ] Code follows the project's coding standards
- [ ] Tests added/updated for changes
- [ ] Documentation updated if needed
- [ ] All CI checks pass
- [ ] PR description clearly explains the changes

## Testing Requirements

### Minimum Coverage

- **Unit tests**: 80% coverage
- **Integration tests**: All API endpoints
- **E2E tests**: Critical user journeys

### Writing Tests

```python
# Python example
def test_screenplay_parser_handles_fountain():
    parser = FountainParser()
    result = parser.parse("INT. OFFICE - DAY\n\nJOHN enters.")
    assert len(result.scenes) == 1
    assert result.scenes[0].location == "OFFICE"
```

```typescript
// TypeScript example
describe('ProjectStore', () => {
  it('should set current project', () => {
    const store = useProjectStore.getState();
    store.setCurrentProject(mockProject);
    expect(store.currentProject).toEqual(mockProject);
  });
});
```

## Architecture Guidelines

### Adding New Features

1. **Check the Master Plan** - Ensure your feature aligns with the documented architecture
2. **Design first** - For significant features, create a design document
3. **Incremental PRs** - Break large features into smaller, reviewable PRs

### File Organization

- Keep related code together
- Follow existing patterns in the codebase
- Place shared utilities in appropriate `utils/` directories

## Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Open a GitHub Issue with reproduction steps
- **Features**: Open a GitHub Issue for discussion first

## Recognition

Contributors will be recognized in:
- The project's CONTRIBUTORS file
- Release notes for significant contributions

Thank you for contributing to SceneMachine.ai!
