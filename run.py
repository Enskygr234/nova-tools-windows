"""PyInstaller ve doğrudan çalıştırma için giriş betiği: python run.py"""
import sys

from nova_tools.main import main

if __name__ == "__main__":
    sys.exit(main())
