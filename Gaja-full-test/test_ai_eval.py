#!/usr/bin/env python3
"""Test AI evaluatora"""

import asyncio
import json
from src.evaluation.ai_evaluator import AIEvaluator

# Symulacja konwersacji jak z logów
conversation = [
    {
        'query': 'Cześć! Jestem Tomek, programista.',
        'response': {
            'success': True,
            'data': {
                'type': 'normal_response',
                'response': '{"text": "Cześć, Tomek! Fajnie cię słyszeć.", "command": "", "params": {}}'
            }
        },
        'timestamp': '2025-01-09T15:00:32',
        'step_index': 0
    }
]

async def test():
    evaluator = AIEvaluator()
    try:
        result = await evaluator.evaluate_conversation(
            conversation,
            'Test scenario',
            ['Be helpful']
        )
        print(f'✅ Test przeszedł: {result.success_percentage}%')
    except Exception as e:
        print(f'❌ Błąd: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
