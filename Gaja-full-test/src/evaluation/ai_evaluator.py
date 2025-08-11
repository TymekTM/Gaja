"""Surowy system oceny AI z lokalnym modelem LM Studio."""

import json
import aiohttp
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from loguru import logger


class EvaluationCriteria(Enum):
    """Kryteria oceny odpowiedzi AI."""
    ACCURACY = "accuracy"  # Czy odpowiedź jest faktycznie poprawna
    RELEVANCE = "relevance"  # Czy odpowiedź jest na temat
    COMPLETENESS = "completeness"  # Czy odpowiedź jest kompletna
    TOOL_USAGE = "tool_usage"  # Czy użyto odpowiednich narzędzi
    CONTEXT_UNDERSTANDING = "context_understanding"  # Czy zrozumiano kontekst
    PROACTIVITY = "proactivity"  # Czy AI działało proaktywnie
    CONVERSATION_FLOW = "conversation_flow"  # Czy rozmowa płynie naturalnie
    ERROR_HANDLING = "error_handling"  # Czy błędy są obsługiwane
    MEMORY_USAGE = "memory_usage"  # Czy używa pamięci kontekstowej
    PERSONALIZATION = "personalization"  # Czy odpowiedź jest spersonalizowana


@dataclass
class EvaluationResult:
    """Wynik oceny pojedynczego kryterium."""
    criteria: EvaluationCriteria
    score: float  # 0.0 - 10.0
    max_score: float  # Maksymalny możliwy wynik
    reasoning: str  # Uzasadnienie oceny
    issues: List[str]  # Lista znalezionych problemów
    suggestions: List[str]  # Sugestie poprawy
    severity: str  # "low", "medium", "high", "critical"


@dataclass
class ConversationEvaluation:
    """Pełna ocena całej konwersacji."""
    conversation_id: str
    scenario_name: str
    total_score: float
    max_possible_score: float
    success_percentage: float
    criteria_results: List[EvaluationResult]
    overall_issues: List[str]
    overall_suggestions: List[str]
    conversation_analysis: str
    critical_failures: List[str]
    passes_quality_gate: bool


class AIEvaluator:
    """Główny ewaluator używający lokalnego modelu LM Studio."""
    
    def __init__(self, lm_studio_url: str = "http://127.0.0.1:1234", model_name: str = "openai/gpt-oss-20b"):
        self.lm_studio_url = lm_studio_url.rstrip('/')
        self.model_name = model_name
        self.quality_gate_threshold = 75.0  # Minimalna ocena żeby przejść
        
    async def test_connection(self) -> bool:
        """Testuje połączenie z LM Studio."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.lm_studio_url}/v1/models") as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [m["id"] for m in data.get("data", [])]
                        if self.model_name in models:
                            logger.info(f"✅ Połączono z LM Studio, model {self.model_name} dostępny")
                            return True
                        else:
                            logger.error(f"❌ Model {self.model_name} niedostępny. Dostępne: {models}")
                            return False
                    return False
        except Exception as e:
            logger.error(f"❌ Błąd połączenia z LM Studio: {e}")
            return False
    
    async def evaluate_conversation(
        self, 
        conversation: List[Dict[str, Any]], 
        scenario_description: str,
        expected_behaviors: Optional[List[str]] = None
    ) -> ConversationEvaluation:
        """Ocenia całą konwersację według wszystkich kryteriów."""
        
        logger.info(f"🔍 Rozpoczynam BEZWZGLĘDNĄ ocenę konwersacji...")
        
        # Sprawdź połączenie
        if not await self.test_connection():
            raise Exception("Nie można połączyć się z LM Studio!")
        
        criteria_results = []
        total_score = 0.0
        max_possible_score = 0.0
        critical_failures = []
        
        # Ocena według każdego kryterium
        for criteria in EvaluationCriteria:
            result = await self._evaluate_single_criteria(
                conversation, 
                scenario_description, 
                criteria,
                expected_behaviors or []
            )
            criteria_results.append(result)
            total_score += result.score
            max_possible_score += result.max_score
            
            # Zbierz krytyczne błędy
            if result.severity == "critical":
                critical_failures.extend(result.issues)
        
        # Analiza ogólna konwersacji
        conversation_analysis = await self._analyze_conversation_flow(conversation, scenario_description)
        
        # Zbierz wszystkie problemy i sugestie
        all_issues = []
        all_suggestions = []
        for result in criteria_results:
            all_issues.extend(result.issues)
            all_suggestions.extend(result.suggestions)
        
        success_percentage = (total_score / max_possible_score * 100) if max_possible_score > 0 else 0
        passes_quality_gate = success_percentage >= self.quality_gate_threshold and len(critical_failures) == 0
        
        evaluation = ConversationEvaluation(
            conversation_id=f"conv_{len(conversation)}",
            scenario_name=scenario_description.split(':')[0] if ':' in scenario_description else scenario_description,
            total_score=total_score,
            max_possible_score=max_possible_score,
            success_percentage=success_percentage,
            criteria_results=criteria_results,
            overall_issues=all_issues,  # Pozostaw bez usuwania duplikatów - mogą być słowniki
            overall_suggestions=all_suggestions,  # Pozostaw bez usuwania duplikatów
            conversation_analysis=conversation_analysis,
            critical_failures=critical_failures,
            passes_quality_gate=passes_quality_gate
        )
        
        # Loguj wynik
        if passes_quality_gate:
            logger.success(f"✅ OCENA POZYTYWNA: {success_percentage:.1f}% ({total_score:.1f}/{max_possible_score:.1f})")
        else:
            logger.error(f"❌ OCENA NEGATYWNA: {success_percentage:.1f}% ({total_score:.1f}/{max_possible_score:.1f})")
            if critical_failures:
                logger.error(f"💥 KRYTYCZNE BŁĘDY: {len(critical_failures)}")
        
        return evaluation
    
    async def _evaluate_single_criteria(
        self, 
        conversation: List[Dict[str, Any]], 
        scenario: str, 
        criteria: EvaluationCriteria,
        expected_behaviors: Optional[List[str]]
    ) -> EvaluationResult:
        """Ocenia konwersację według pojedynczego kryterium."""
        
        prompt = self._build_evaluation_prompt(conversation, scenario, criteria, expected_behaviors or [])
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model_name,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Jesteś BEZWZGLĘDNYM oceniaczem AI asystentów. Twoja praca to znalezienie każdego błędu i niedociągnięcia. Bądź surowy jak najgorszy krytyk. Oceniaj jak profesor na egzaminie doktorskim - każdy błąd to znaczne obniżenie oceny. NIE BĄDŹ ŁAGODNY!"
                        },
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ],
                    "temperature": 0.1,  # Niska temperatura dla konsystentnych ocen
                    "max_tokens": 2000
                }
                
                async with session.post(
                    f"{self.lm_studio_url}/v1/chat/completions",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        result_text = data["choices"][0]["message"]["content"]
                        return self._parse_evaluation_result(result_text, criteria)
                    else:
                        error_text = await response.text()
                        raise Exception(f"LM Studio error {response.status}: {error_text}")
            
        except Exception as e:
            logger.error(f"Błąd oceny {criteria.value}: {e}")
            return EvaluationResult(
                criteria=criteria,
                score=0.0,
                max_score=10.0,
                reasoning=f"Błąd podczas oceny: {e}",
                issues=[f"Nie udało się ocenić {criteria.value}"],
                suggestions=["Sprawdź połączenie z LM Studio"],
                severity="critical"
            )
    
    def _build_evaluation_prompt(
        self, 
        conversation: List[Dict[str, Any]], 
        scenario: str, 
        criteria: EvaluationCriteria,
        expected_behaviors: Optional[List[str]]
    ) -> str:
        """Buduje surowy prompt dla konkretnego kryterium oceny."""
        
        # Przygotuj konwersację w czytelnym formacie
        conversation_text = ""
        for i, turn in enumerate(conversation, 1):
            user_msg = turn.get('query', turn.get('message', 'BRAK WIADOMOŚCI'))
            
            # Wyciągnij odpowiedź AI z zagnieżdżonej struktury
            ai_response = "BRAK ODPOWIEDZI"
            if 'response' in turn:
                resp_data = turn['response']
                if isinstance(resp_data, dict):
                    if 'data' in resp_data and isinstance(resp_data['data'], dict):
                        ai_response = resp_data['data'].get('response', 'BRAK ODPOWIEDZI')
                    else:
                        ai_response = str(resp_data)
                else:
                    ai_response = str(resp_data)
            
            conversation_text += f"\n=== TURA {i} ===\n👤 UŻYTKOWNIK: {user_msg}\n🤖 GAJA AI: {ai_response}\n"
        
        criteria_descriptions = {
            EvaluationCriteria.ACCURACY: """
            🎯 KRYTERIUM: DOKŁADNOŚĆ FAKTYCZNA [MAKSYMALNA SUROWOŚĆ]
            SPRAWDŹ BEZWZGLĘDNIE:
            ❌ Czy KAŻDA informacja jest w 100% poprawna faktycznie
            ❌ Czy daty, liczby, fakty są ABSOLUTNIE zgodne z rzeczywistością  
            ❌ Czy nie ma ANI JEDNEGO błędu merytorycznego
            ❌ Czy nie ma ŻADNYCH halucynacji lub wymyślonych informacji
            ❌ Czy AI nie podaje informacji których nie może wiedzieć
            
            OCENA: Jeśli znajdziesz JAKIKOLWIEK błąd faktyczny → DRASTYCZNIE obniż ocenę!
            """,
            EvaluationCriteria.RELEVANCE: """
            🎯 KRYTERIUM: TRAFNOŚĆ ODPOWIEDZI [ZERO TOLERANCJI]
            SPRAWDŹ BEZWZGLĘDNIE:
            ❌ Czy KAŻDA odpowiedź BEZPOŚREDNIO odpowiada na pytanie
            ❌ Czy AI NIE odchodzi od tematu ANI PRZEZ CHWILĘ
            ❌ Czy nie ma ŻADNYCH niepotrzebnych informacji
            ❌ Czy KAŻDE słowo służy realizacji żądania użytkownika
            ❌ Czy AI nie gada o rzeczach o które nie pytano
            
            OCENA: Każde zejście z tematu = DUŻE obniżenie oceny!
            """,
            EvaluationCriteria.COMPLETENESS: """
            🎯 KRYTERIUM: KOMPLETNOŚĆ [PERFEKCJONIZM WYMAGANY]
            SPRAWDŹ BEZWZGLĘDNIE:
            ❌ Czy odpowiedź realizuje WSZYSTKIE elementy żądania
            ❌ Czy nie pominięto ŻADNEGO ważnego elementu
            ❌ Czy wszystkie wymagane informacje są dostarczone
            ❌ Czy poziom szczegółowości jest IDEALNY (nie za mało, nie za dużo)
            ❌ Czy żądanie zostało zrealizowane w 100%
            
            OCENA: Każdy brakujący element = DRASTYCZNE obniżenie!
            """,
            EvaluationCriteria.TOOL_USAGE: """
            🎯 KRYTERIUM: UŻYWANIE NARZĘDZI [MAKSYMALNA PRECYZJA]
            SPRAWDŹ BEZWZGLĘDNIE:
            ❌ Czy AI używa DOKŁADNIE odpowiednich narzędzi gdy powinno
            ❌ Czy NIE używa narzędzi gdy nie powinno (overhead)
            ❌ Czy wybiera NAJLEPSZE dostępne narzędzie
            ❌ Czy poprawnie interpretuje wyniki z narzędzi
            ❌ Czy informuje użytkownika o użyciu narzędzi gdy trzeba
            
            OCENA: Każde złe użycie/brak użycia narzędzia = DUŻA kara!
            """,
            EvaluationCriteria.CONTEXT_UNDERSTANDING: """
            🎯 KRYTERIUM: ZROZUMIENIE KONTEKSTU [INTELIGENCJA WYMAGANA]
            SPRAWDŹ BEZWZGLĘDNIE:
            ❌ Czy AI rozumie PEŁNY kontekst każdej rozmowy
            ❌ Czy nawiązuje do wcześniejszych wypowiedzi PRECYZYJNIE
            ❌ Czy pamięta WSZYSTKIE wcześniejsze ustalenia
            ❌ Czy interpretuje zamiary użytkownika TRAFNIE
            ❌ Czy buduje na kontekście w sposób INTELIGENTNY
            
            OCENA: Każda utrata kontekstu = POWAŻNE obniżenie!
            """,
            EvaluationCriteria.PROACTIVITY: """
            🎯 KRYTERIUM: PROAKTYWNOŚĆ [INICJATYWA WYMAGANA]  
            SPRAWDŹ BEZWZGLĘDNIE:
            ❌ Czy AI proponuje MĄDRE dodatkowe akcje
            ❌ Czy antycypuje potrzeby użytkownika TRAFNIE
            ❌ Czy sugeruje powiązane funkcjonalności SENSOWNIE
            ❌ Czy działa nie tylko reaktywnie ale PRZEWIDUJE
            ❌ Czy inicjatywa AI jest WARTOŚCIOWA a nie irytująca
            
            OCENA: Brak proaktywności = średnia ocena. Zła proaktywność = duża kara!
            """,
            EvaluationCriteria.CONVERSATION_FLOW: """
            🎯 KRYTERIUM: PŁYNNOŚĆ KONWERSACJI [NATURALNOŚĆ WYMAGANA]
            SPRAWDŹ BEZWZGLĘDNIE:
            ❌ Czy rozmowa płynie ABSOLUTNIE naturalnie
            ❌ Czy odpowiedzi są spójne stylistycznie w 100%
            ❌ Czy ton jest PERFEKCYJNIE odpowiedni i konsekwentny
            ❌ Czy nie ma ŻADNYCH nielogicznych przeskoków
            ❌ Czy AI brzmi jak kompetentny asystent a nie bot
            
            OCENA: Każda nienaturalność = obniżenie! Brzmi jak bot = duża kara!
            """,
            EvaluationCriteria.ERROR_HANDLING: """
            🎯 KRYTERIUM: OBSŁUGA BŁĘDÓW [PROFESJONALIZM WYMAGANY]
            SPRAWDŹ BEZWZGLĘDNIE:
            ❌ Czy AI obsługuje błędy w sposób GRACEFUL
            ❌ Czy informuje o problemach ZROZUMIALE dla użytkownika
            ❌ Czy próbuje alternatywnych rozwiązań MĄDRZE
            ❌ Czy NIE zostawia użytkownika bez pomocnej informacji
            ❌ Czy błędy nie psują całego doświadczenia
            
            OCENA: Każdy źle obsłużony błąd = DUŻA kara!
            """,
            EvaluationCriteria.MEMORY_USAGE: """
            🎯 KRYTERIUM: UŻYWANIE PAMIĘCI [INTELIGENCJA DŁUGOTERMINOWA]
            SPRAWDŹ BEZWZGLĘDNIE:
            ❌ Czy AI pamięta wcześniejsze interakcje PRECYZYJNIE  
            ❌ Czy wykorzystuje informacje z poprzednich rozmów MĄDRZE
            ❌ Czy buduje na kontekście długoterminowym SENSOWNIE
            ❌ Czy personalizuje na bazie historii TRAFNIE
            ❌ Czy nie zapomina ważnych rzeczy w trakcie rozmowy
            
            OCENA: Każda utrata pamięci = POWAŻNE obniżenie!
            """,
            EvaluationCriteria.PERSONALIZATION: """
            🎯 KRYTERIUM: PERSONALIZACJA [INDYWIDUALNE PODEJŚCIE]
            SPRAWDŹ BEZWZGLĘDNIE:
            ❌ Czy odpowiedzi są IDEALNIE dostosowane do użytkownika
            ❌ Czy uwzględnia preferencje użytkownika DOKŁADNIE
            ❌ Czy ton i styl są PERFEKCYJNIE odpowiednie
            ❌ Czy używa informacji o użytkowniku SENSOWNIE
            ❌ Czy personalizacja NIE jest natrętna lub niewłaściwa
            
            OCENA: Brak personalizacji lub zła personalizacja = obniżenie!
            """
        }
        
        return f"""
🔥 MISJA: BEZWZGLĘDNA OCENA ASYSTENTA AI 🔥

SCENARIUSZ TESTOWY: {scenario}

OCZEKIWANE ZACHOWANIA (te MUSZĄ być spełnione):
{chr(10).join(f"✅ {behavior}" for behavior in (expected_behaviors or []))}

{criteria_descriptions[criteria]}

KONWERSACJA DO SUROWEJ OCENY:
{conversation_text}

🎯 ZADANIE OCENIAJĄCE:
Oceń powyższą konwersację BEZWZGLĘDNIE według kryterium {criteria.value}. 
Bądź MAKSYMALNIE surowy - to nie jest ocena koleżeńska ale profesjonalna!
Znajdź KAŻDY błąd, każde niedociągnięcie, każdą słabość!

ZASADY OCENIANIA:
• 0-2 pkt = KATASTROFA (całkowite niepowodzenie)
• 3-4 pkt = BARDZO ZŁE (większość nie działa)
• 5-6 pkt = ZŁE (kilka rzeczy działa, ale dużo problemów)
• 7-8 pkt = PRZECIĘTNE (w porządku ale widoczne problemy)  
• 9-10 pkt = DOSKONAŁE (prawie/całkowicie bezbłędne)

NIE BĄDŹ ŁAGODNY! Każdy błąd to obniżenie!

ODPOWIEDZ DOKŁADNIE W TYM FORMACIE JSON:
{{
    "score": X.X,
    "max_score": 10.0,
    "reasoning": "BARDZO szczegółowe uzasadnienie - dlaczego taka ocena, co dokładnie nie gra, co jest dobre a co złe",
    "issues": ["Lista KONKRETNYCH problemów jakie znalazłeś", "Każdy problem opisz dokładnie"],
    "suggestions": ["Lista KONKRETNYCH sugestii jak to naprawić", "Każda sugestia konkretna i wykonalna"],
    "severity": "low/medium/high/critical"
}}

UWAGA: Jeśli znajdziesz POWAŻNE błędy → severity = "critical" i ocena musi być drastycznie niska!
"""
    
    def _parse_evaluation_result(self, result_text: str, criteria: EvaluationCriteria) -> EvaluationResult:
        """Parsuje odpowiedź modelu do struktury EvaluationResult."""
        try:
            # Znajdź JSON w odpowiedzi (może być otoczony tekstem)
            json_start = result_text.find('{')
            json_end = result_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = result_text[json_start:json_end]
                
                # Sprawdź czy JSON jest poprawny, jeśli nie - spróbuj naprawić
                try:
                    data = json.loads(json_str)
                except json.JSONDecodeError:
                    # Spróbuj wyciągnąć tylko pierwszą strukturę JSON
                    bracket_count = 0
                    end_pos = json_start
                    for i, char in enumerate(json_str):
                        if char == '{':
                            bracket_count += 1
                        elif char == '}':
                            bracket_count -= 1
                            if bracket_count == 0:
                                end_pos = json_start + i + 1
                                break
                    
                    json_str = result_text[json_start:end_pos]
                    data = json.loads(json_str)
                
                return EvaluationResult(
                    criteria=criteria,
                    score=float(data.get('score', 0.0)),
                    max_score=float(data.get('max_score', 10.0)),
                    reasoning=data.get('reasoning', 'Brak uzasadnienia'),
                    issues=data.get('issues', []),
                    suggestions=data.get('suggestions', []),
                    severity=data.get('severity', 'medium')
                )
            else:
                raise ValueError("Nie znaleziono JSON w odpowiedzi")
                
        except Exception as e:
            logger.error(f"Błąd parsowania wyniku dla {criteria.value}: {e}")
            logger.debug(f"Surowa odpowiedź: {result_text}")
            
            return EvaluationResult(
                criteria=criteria,
                score=0.0,
                max_score=10.0,
                reasoning=f"Błąd parsowania odpowiedzi: {e}",
                issues=[f"Model nie odpowiedział w poprawnym formacie"],
                suggestions=["Sprawdź poprawność prompta i modelu"],
                severity="critical"
            )
    
    async def _analyze_conversation_flow(self, conversation: List[Dict[str, Any]], scenario: str) -> str:
        """Analizuje ogólny przebieg konwersacji z maksymalną surowością."""
        
        conversation_text = ""
        for i, turn in enumerate(conversation, 1):
            user_msg = turn.get('query', turn.get('message', 'BRAK'))
            
            ai_response = "BRAK ODPOWIEDZI"
            if 'response' in turn:
                resp_data = turn['response']
                if isinstance(resp_data, dict) and 'data' in resp_data:
                    ai_response = resp_data['data'].get('response', 'BRAK ODPOWIEDZI')
                else:
                    ai_response = str(resp_data)
            
            conversation_text += f"\nTURA {i}:\n👤 {user_msg}\n🤖 {ai_response}\n"
        
        prompt = f"""
🔥 BEZWZGLĘDNA ANALIZA CAŁEJ KONWERSACJI 🔥

SCENARIUSZ: {scenario}

KONWERSACJA:
{conversation_text}

🎯 ZADANIE:
Przeanalizuj całą konwersację jako CIĄGŁY PRZEPŁYW z maksymalną surowością.
Bądź jak najgorszy krytyk - znajdź każdy problem!

SKONCENTRUJ SIĘ NA:
1. Czy konwersacja FAKTYCZNIE realizuje założenia scenariusza? 
2. Jakie są WSZYSTKIE problemy w przepływie rozmowy?
3. Czy AI brzmi kompetentnie czy jak niedouczony bot?
4. Czy logika konwersacji jest spójna?
5. Ogólny poziom profesjonalizmu (bądź surowy!)

Napisz 3-4 zdania SUROWEJ analizy. Nie oszczędzaj krytyki!
Jeśli coś jest źle - powiedz to wprost i bezwzględnie!
"""
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 1000
                }
                
                async with session.post(
                    f"{self.lm_studio_url}/v1/chat/completions",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        return f"Błąd analizy: HTTP {response.status}"
        except Exception as e:
            return f"Błąd analizy konwersacji: {e}"
