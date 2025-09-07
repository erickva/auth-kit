from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="auth-kit-fastapi",
    version="0.3.2",
    author="Erick Ama",
    author_email="me@erick.no",
    description="FastAPI authentication backend for Auth Kit",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/erickva/auth-kit",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Framework :: FastAPI",
    ],
    python_requires=">=3.8",
    install_requires=[
        "fastapi>=0.100.0",
        "sqlalchemy>=2.0.0",
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "python-jose[cryptography]>=3.3.0",
        "passlib[bcrypt]>=1.7.4",
        "python-multipart>=0.0.6",
        "email-validator>=2.0.0",
        "pyotp>=2.9.0",
        "qrcode>=7.4.0",
        "webauthn>=1.9.0",
        "alembic>=1.12.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "httpx>=0.24.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "redis": ["redis>=4.5.0"],
        "postgres": ["psycopg2-binary>=2.9.0"],
        "mysql": ["pymysql>=1.1.0"],
    },
)
