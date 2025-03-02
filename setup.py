from setuptools import setup, find_packages

setup(
    name="selenium-space-calls",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'selenium>=4.15.2',
        'openai>=1.3.0',
        'pytest>=7.4.0',
        'pytest-asyncio>=0.21.1',
        'SpeechRecognition>=3.10.0',
        'gTTS>=2.3.2',
        'PyAudio>=0.2.13',
        'numpy>=1.24.0',
        'python-dotenv>=1.0.0',
        'requests>=2.31.0',
        'websockets>=11.0.3',
        'aiohttp>=3.9.1',
        'pytest-mock>=3.11.1',
        'pytest-cov>=4.1.0',
        'torch>=2.0.1',
        'torchaudio>=2.0.1',
        'transformers>=4.31.0',
        'pyannote.audio>=3.0.1',
        'sounddevice>=0.4.6',
        'msedge-selenium-tools>=3.141.4',
        'webdriver-manager>=4.0.0',
        'watchdog>=3.0.0'
    ],
    python_requires='>=3.8',
) 