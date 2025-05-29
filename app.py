import streamlit as st
from llama_index.indices.managed.llama_cloud import LlamaCloudIndex
from llama_index.core import Settings
from llama_index.llms.openai import OpenAI
from llama_index.core.prompts import PromptTemplate
import json
import os

# Конфигурация индекса
INDEX_NAME = "Arxiv(Vilatility) 28/05"
PROJECT_NAME = "Default"
ORGANIZATION_ID = "3fee475d-903c-4b04-b81a-50c133aca474"

# Кастомный системный промпт для детальных ответов на русском языке
DETAILED_QA_PROMPT = PromptTemplate(
    """\
Ты - эксперт в области финансов и портфельного управления. Твоя задача - предоставить исчерпывающий, подробный и академически точный ответ НА РУССКОМ ЯЗЫКЕ на основе предоставленного контекста.

ВАЖНО: ОТВЕЧАЙ ТОЛЬКО НА РУССКОМ ЯЗЫКЕ!

ИНСТРУКЦИИ ПО ОТВЕТУ:
1. Предоставь подробное и всестороннее объяснение на русском языке
2. Структурируй ответ с четкими подзаголовками
3. Включи конкретные примеры, цифры и формулы из документов
4. Объясни практическое применение и значимость
5. Укажи преимущества и недостатки (если применимо)
6. Используй академический стиль с доступными объяснениями
7. Переводи все английские термины на русский с пояснением в скобках
8. Если информации недостаточно, четко укажи это

СТРУКТУРА ОТВЕТА НА РУССКОМ ЯЗЫКЕ:
- **Определение**: Четкое определение термина/концепции
- **Принципы работы**: Как это функционирует
- **Математические основы**: Формулы и расчеты (если есть)
- **Практические примеры**: Конкретные случаи из документов
- **Преимущества и недостатки**: Объективный анализ
- **Применение**: Где и как используется
- **Связь с другими концепциями**: Контекст в общей теории

КОНТЕКСТ ДОКУМЕНТОВ:
{context_str}

ВОПРОС ПОЛЬЗОВАТЕЛЯ:
{query_str}

ДЕТАЛЬНЫЙ ОТВЕТ НА РУССКОМ ЯЗЫКЕ:
"""
)

def get_api_keys():
    """Получаем API ключи из секретов Streamlit"""
    try:
        llamaindex_key = st.secrets["LLAMAINDEX_API_KEY"]
        openai_key = st.secrets["OPENAI_API_KEY"]
        
        # Устанавливаем OpenAI ключ в переменную окружения
        os.environ["OPENAI_API_KEY"] = openai_key
        
        return llamaindex_key, openai_key
    except KeyError as e:
        st.error(f"🔑 **API ключ не найден:** {str(e)}")
        st.markdown("""
        **Добавьте следующие ключи в настройки Streamlit Cloud:**
        
        ```toml
        LLAMAINDEX_API_KEY = "ваш-llamaindex-ключ"
        OPENAI_API_KEY = "ваш-openai-ключ"
        ```
        
        **Как добавить:**
        1. Откройте ваше приложение на share.streamlit.io
        2. Нажмите меню (⋯) → Settings
        3. Перейдите в раздел "Secrets"
        4. Вставьте ваши реальные API ключи
        5. Сохраните и перезапустите приложение
        """)
        st.stop()
        return None, None

@st.cache_resource
def initialize_index():
    """Инициализируем индекс один раз и кешируем"""
    llamaindex_key, openai_key = get_api_keys()
    
    if not llamaindex_key or not openai_key:
        return None
        
    try:
        # Настраиваем OpenAI LLM с оптимальными параметрами для русского языка
        llm = OpenAI(
            model="gpt-4",  # Используем GPT-4 для лучшего качества
            temperature=0.1,  # Низкая температура для точности
            max_tokens=3000,  # Увеличиваем лимит для детальных ответов
        )
        Settings.llm = llm
        
        # Создаем индекс
        index = LlamaCloudIndex(
            name=INDEX_NAME,
            project_name=PROJECT_NAME,
            organization_id=ORGANIZATION_ID,
            api_key=llamaindex_key,
        )
        
        return index
    except Exception as e:
        st.error(f"❌ Ошибка инициализации индекса: {str(e)}")
        return None

def create_enhanced_query_engine(index):
    """Создает настроенный query engine с улучшенными параметрами"""
    return index.as_query_engine(
        similarity_top_k=30,  # Больше релевантных документов
        response_mode="tree_summarize",  # Лучший режим для детальных ответов
        text_qa_template=DETAILED_QA_PROMPT,  # Кастомный промпт для русского языка
        streaming=False,  # Отключаем streaming для полных ответов
        use_async=False,
    )

def query_llamaindex(question: str) -> dict:
    """Отправляет запрос к LlamaIndex и возвращает ответ на русском языке"""
    
    index = initialize_index()
    if not index:
        return {
            "response": "❌ Не удалось подключиться к индексу",
            "sources": []
        }
    
    try:
        # Создаем улучшенный query engine
        query_engine = create_enhanced_query_engine(index)
        
        # Получаем полноценный ответ
        response = query_engine.query(question)
        
        return {
            "response": str(response.response) if response.response else "Не удалось сгенерировать ответ",
            "sources": []  # Не собираем источники
        }
        
    except Exception as e:
        return {
            "response": f"⚠️ Ошибка при обработке запроса: {str(e)}",
            "sources": []
        }

def format_response(result: dict) -> str:
    """Форматирует ответ без источников"""
    return result["response"]

def main():
    st.set_page_config(
        page_title="Arxiv+Llama+OpenAI Q/A assist",
        page_icon="🤖",
        layout="wide"
    )
    
    st.title("🤖 Arxiv+Llama+OpenAI Q/A assist")
    st.markdown("💡 **Раз раз это хардбас**")
    
    # Проверяем API ключи при запуске
    llamaindex_key, openai_key = get_api_keys()
    
    # Проверяем подключение к индексу
    index = initialize_index()
    if not index:
        st.error("Не удалось подключиться к индексу. Проверьте API ключи.")
        return
    
    # Инициализация истории чата
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Отображение истории чата
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Поле для ввода вопроса
    if prompt := st.chat_input("Задайте вопрос о финансах и инвестициях..."):
        # Добавляем сообщение пользователя
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Получаем ответ от LlamaIndex
        with st.chat_message("assistant"):
            with st.spinner("🔍 Анализ..."):
                result = query_llamaindex(prompt)
                formatted_response = format_response(result)
            st.markdown(formatted_response)
        
        # Добавляем ответ в историю
        st.session_state.messages.append({"role": "assistant", "content": formatted_response})
    
    # Боковая панель с информацией
    with st.sidebar:
        st.header("⚙️ Настройки эксперта")
        
        # Статус подключения к API
        try:
            llamaindex_key = st.secrets["LLAMAINDEX_API_KEY"]
            openai_key = st.secrets["OPENAI_API_KEY"]
            
            st.success("🔑 LlamaIndex подключен")
            st.success("🧠 GPT-4 активен")
            st.success("🇷🇺 Режим русского языка")
            st.success("📄 Источники скрыты")
            
            if index:
                st.success("🔗 Индекс готов")
                
        except:
            st.error("❌ API ключи не настроены")
        
        # Настройки ответов
        st.markdown("---")
        st.markdown("### ⚙️ Параметры ответов")
        st.text("📈 Источников: 12")
        st.text("🎯 Режим: tree_summarize") 
        st.text("🧠 Модель: GPT-4")
        st.text("🌡️ Температура: 0.1")
        st.text("📝 Макс. токены: 3000")
        st.text("🇷🇺 Язык: Русский")
        st.text("📚 Источники: Скрыты")
        
        if st.button("🗑️ Очистить чат"):
            st.session_state.messages = []
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 📊 Статистика")
        st.write(f"💬 Сообщений: {len(st.session_state.messages)}")
        
        st.markdown("---")
        st.markdown("### 💡 Примеры вопросов")
        
        example_questions = [
            "Расскажи подробно об инвестиционных стратегиях",
            "Что такое равновзвешенная инвестиционная стратегия?",
            "Объясни методы минимизации дисперсии портфеля",
            "Как работает динамическое хеджирование волатильности?",
            "В чем разница между статическими и динамическими стратегиями?",
            "Объясни принципы максимальной диверсификации портфеля"
        ]
        
        for question in example_questions:
            if st.button(f"📝 {question}", key=f"example_{hash(question)}"):
                # Добавляем вопрос в чат
                st.session_state.messages.append({"role": "user", "content": question})
                # Получаем ответ
                with st.spinner("🔍 Генерирую экспертный ответ..."):
                    result = query_llamaindex(question)
                    formatted_response = format_response(result)
                st.session_state.messages.append({"role": "assistant", "content": formatted_response})
                st.rerun()
        
        st.markdown("---")
        st.markdown("### ℹ️ О системе")
        st.markdown("""
        **🧠 ИИ:** GPT-4 с промптами на русском языке
        
        **📚 База знаний:** Arxiv
        
        **🔍 Анализ:** 30 релевантных источников
        
        **📄 Формат:** Без отображения источников
        
        """)

if __name__ == "__main__":
    main()
