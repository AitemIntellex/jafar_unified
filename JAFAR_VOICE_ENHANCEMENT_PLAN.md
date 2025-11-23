# Jafar Voice Assistant Enhancement Plan

This document outlines the development roadmap for improving the Jafar voice assistant, evolving it from a command-executor into a contextual AI partner for market analysis and trading.

## Core Idea: State & Context

The key principle behind all enhancements is **state management**. Jafar must understand the context of the conversation and operate in different modes to provide relevant and intelligent responses.

---

## Development Roadmap

### Stage 1: Mode Management (Foundation)

-   **Status:** `Pending`
-   **Goal:** Implement a foundational state manager that allows Jafar to switch between different operational modes. This will control its personality, focus, and the underlying prompts sent to the Gemini API.

#### Proposed Modes:

1.  **`ANALITIK REJIMI` (Analyst Mode):**
    -   **Activation Phrase:** "Jafar, analitik rejimiga o't"
    -   **Behavior:** Ultra-focused on market data. Gemini prompts will be primed for concise, data-driven analysis. Casual conversation is deprioritized. All non-command phrases are interpreted as analytical queries.

2.  **`SUHBATDOSH REJIMI` (Conversational Mode):**
    -   **Activation Phrase:** "Suhbatdosh rejimiga o't"
    -   **Behavior:** Enables debates, discussions, and arguments. The Gemini prompt is changed to encourage a witty, knowledgeable, and even argumentative personality, fostering stimulating discussions rather than just Q&A.

3.  **`SAVDO REJIMI` (Trading Mode):**
    -   **Activation Phrase:** "Savdo rejimiga o't"
    -   **Behavior:** A proactive mode focused on execution. Jafar will actively use `btrade` to manage and monitor positions. New voice commands like "pozitsiyani tekshir" (check position) will be enabled.

---

### Stage 2: Interactive Dialogue Scenarios

-   **Status:** `Pending`
-   **Goal:** Move away from immediate command execution to interactive, multi-turn dialogues for complex actions.

#### Example Scenario (`atrade` analysis):

1.  **User:** "Jafar, tahlil qilamiz." (Let's do an analysis.)
2.  **Jafar:** "Albatta. Skrinshotlar uchun ekranni tayyorlab, menga xabar bering." (Of course. Prepare your screen for screenshots and let me know.) -> *State changes to `AWAITING_SCREENSHOT_CONFIRMATION`*.
3.  **User:** "Men tayyorman." (I'm ready.)
4.  **Jafar:** "Ajoyib. Birinchi skrinshot 3 soniyadan so'ng..." (Excellent. First screenshot in 3 seconds...) -> *Initiates the screenshot process.*

---

### Stage 3: Contextual Memory

-   **Status:** `Pending`
-   **Goal:** Enable Jafar to remember the context of the current and previous conversations to provide more relevant and intelligent follow-up responses.

#### Technical Implementation:

-   Persist summaries of analyses and key conversation points.
-   Inject this "memory" as context into future Gemini prompts.

#### Example Dialogue:

-   *(...After completing a BUY analysis for Gold...)*
-   **User (15 mins later):** "Jafar, vaziyat qanday?" (Jafar, what's the situation?)
-   **Jafar (recalling the context):** "Oltin bo'yicha bizning BUY rejamiz hali ham kuchda. Narx kirish nuqtasiga yaqinlashmoqda. Yangiliklarni tekshirib ko'raymi?" (Our BUY plan for Gold is still valid. The price is approaching our entry point. Should I check the news?)

---

### Stage 4: Proactive Actions (Advanced)

-   **Status:** `Pending`
-   **Goal:** (Long-term) Develop a mechanism for Jafar to initiate conversations based on real-time market events.

#### Example Proactive Alert:

-   **Jafar (interrupting):** "Janob, diqqat! AQShda inflyatsiya bo'yicha ma'lumotlar chiqdi. Bu bizning pozitsiyamizga ta'sir qilishi mumkin." (Sir, attention! US inflation data has been released. This could impact our position.)

---
*This plan will be updated as features are implemented.*
