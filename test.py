try:
    from dotenv import load_dotenv
    print("✅ Библиотека найдена!")
    print("Путь:", __import__('dotenv').__file__)
except ImportError as e:
    print("❌ Ошибка:", e)
    print("🔍 Где ищет Python:")
    import sys
    for path in sys.path:
        print("   ", path)