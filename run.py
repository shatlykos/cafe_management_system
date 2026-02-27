#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Главный файл для запуска системы управления кафе
"""

import sys
import os

try:
    from cli import main
    if __name__ == "__main__":
        main()
except KeyboardInterrupt:
    print("\n\nProgram interrupted by user.")
    try:
        input("\nPress Enter to exit...")
    except:
        pass
    sys.exit(0)
except ImportError as e:
    print(f"\nERROR: Cannot import modules: {e}")
    print("\nMake sure all files are in the same folder.")
    try:
        input("\nPress Enter to exit...")
    except:
        pass
    sys.exit(1)
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
    try:
        input("\nPress Enter to exit...")
    except:
        pass
    sys.exit(1)

