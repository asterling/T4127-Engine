# Contributing to Canada Pay Freedom

Thanks for your interest in contributing! This project is an open-source Canadian payroll application. Contributions of all kinds are welcome — bug fixes, new features, documentation, and test improvements.

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+ (for the React frontend)
- Docker (optional, for containerized setup)

### Local Development Setup

```bash
# Clone the repo
git clone https://github.com/asterling/T4127-Engine.git
cd canada-pay-freedom

# Install Python dependencies
pip install -r payroll_app/requirements.txt

# Install frontend dependencies
cd payroll_app/frontend
npm install
cd ../..

# Run the demo (populates sample data + starts servers)
./run_demo.sh
```

The app will be available at:
- React frontend: http://localhost:5173
- API backend: http://localhost:8200
- API docs: http://localhost:8200/docs

### Running Tests

```bash
# All payroll app tests
python -m pytest payroll_app/tests/ -v

# Payroll calculator tests (fast)
python -m pytest payroll_calc/tests/test_regression.py -v

# Exhaustive CRA validation (slower, 90K+ scenarios)
python -m pytest payroll_calc/tests/test_t4032_exhaustive.py -v
```

## How to Contribute

### Reporting Bugs

- Open a GitHub Issue with a clear title and description
- Include steps to reproduce, expected vs. actual behavior
- Mention the province and pay period if it's a calculation issue

### Submitting Changes

1. Fork the repository
2. Create a feature branch from `main` (`git checkout -b feature/my-change`)
3. Make your changes
4. Write or update tests for your changes
5. Run the test suite and make sure all tests pass
6. Commit with a clear message describing what and why
7. Open a Pull Request against `main`

### PR Guidelines

- Keep PRs focused — one feature or fix per PR
- Include tests for new functionality
- Update the README if your change affects setup, usage, or features
- For payroll calculation changes, validate against CRA's PDOC (Payroll Deductions Online Calculator)

## Code Style

- Python: follow existing patterns in the codebase (type hints, docstrings on public functions)
- TypeScript/React: follow existing component patterns
- No linter is enforced yet — just match the surrounding code

## Areas Where Help Is Especially Welcome

- **Quebec payroll support** — Revenu Quebec tax formulas (TP-1015.3), QPP, QPIP, RL-1 slips
- **Garnishment handling** — court-ordered wage garnishments with CRA priority rules
- **Test coverage** — Selenium tests for onboarding flow, additional PDOC validation scenarios
- **Documentation** — user guides, API docs, architecture decision records

See `TODO.md` files in each package for the full backlog.

## License

By contributing, you agree that your contributions will be licensed under the [AGPL-3.0](LICENSE) license.
