# Contributing to DCS Natural Language ATC

Thank you for your interest in contributing! This project follows Test-Driven Development (TDD) principles.

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Xyrces/dcsAiComms.git
   cd dcsAiComms
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -e ".[dev]"
   ```

4. **Install pre-commit hooks**
   ```bash
   pre-commit install
   ```

## TDD Workflow

We strictly follow Test-Driven Development:

### 1. Red Phase - Write Failing Tests
```python
# tests/test_new_feature.py
def test_new_feature():
    """Test that new feature works correctly"""
    result = new_feature()
    assert result == expected_value
```

### 2. Green Phase - Make Tests Pass
```python
# src/new_feature.py
def new_feature():
    """Implement feature to pass tests"""
    return expected_value
```

### 3. Refactor Phase - Clean Up
- Improve code quality
- Add documentation
- Optimize performance
- Ensure all tests still pass

## Contribution Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Write tests first**
   - Add tests to appropriate file in `tests/`
   - Run tests to confirm they fail: `pytest`

3. **Implement the feature**
   - Write minimal code to pass tests
   - Run tests: `pytest`
   - Refactor and improve

4. **Ensure quality**
   ```bash
   # Run tests
   pytest -v --cov=src

   # Check formatting
   black --check src/ tests/

   # Check style
   flake8 src/ tests/

   # Run all pre-commit checks
   pre-commit run --all-files
   ```

5. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: Add new feature with tests"
   ```

   Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation
   - `test:` - Tests
   - `refactor:` - Code refactoring
   - `style:` - Formatting
   - `chore:` - Maintenance

6. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a Pull Request on GitHub.

## Code Style

- **Python**: Follow PEP 8
- **Line length**: 120 characters
- **Formatting**: Black
- **Linting**: Flake8
- **Type hints**: Use where appropriate
- **Docstrings**: Google style

## Testing Guidelines

- **Coverage**: Maintain >70% code coverage
- **Test types**:
  - Unit tests: Fast, isolated
  - Integration tests: Test component interaction
  - Mark slow tests: `@pytest.mark.slow`

- **Test structure**:
  ```python
  def test_feature_behavior():
      # Arrange
      setup_data = create_test_data()

      # Act
      result = feature_function(setup_data)

      # Assert
      assert result == expected_outcome
  ```

## Documentation

- Update README.md for user-facing changes
- Add docstrings to all public functions/classes
- Update CHANGELOG.md (follows [Keep a Changelog](https://keepachangelog.com/))

## Pull Request Checklist

- [ ] Tests written and passing
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Pre-commit hooks pass
- [ ] CI/CD pipeline passes

## Getting Help

- **Issues**: Check existing issues or create new ones
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: See docs/ directory

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow

## License

By contributing, you agree that your contributions will be licensed under the project's license.

---

**Thank you for contributing to DCS Natural Language ATC!** 🎉
