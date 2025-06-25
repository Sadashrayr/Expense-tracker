import pandas as pd
import os
import re
from dotenv import load_dotenv
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain.agents.agent import AgentExecutor
from langchain_groq import ChatGroq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def load_expense_dataframe():
    """
    Placeholder if needed later for global data access.
    """
    return pd.DataFrame()

def get_agent(df: pd.DataFrame):
    """
    Create a LangChain agent using Groq LLM and your DataFrame.
    """
    llm = ChatGroq(
        temperature=0,
        model_name="deepseek-r1-distill-llama-70b",  # You can switch to "llama3-70b-8192"
        api_key=GROQ_API_KEY
    )

    # Enable output parsing error handling to avoid crashing
    agent = create_pandas_dataframe_agent(
        llm,
        df,
        verbose=False,
        allow_dangerous_code=True,
        handle_parsing_errors=True
    )

    return AgentExecutor(
        agent=agent.agent,
        tools=agent.tools,
        verbose=True,
        handle_parsing_errors=True
    )


def ask_question(agent, question, df=None):
    """
    Handle AI summary questions or forward to LangChain agent.
    """
    try:
        # Match: "summary of my May 2025 expenses"
        summary_match = re.search(r"summary.*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{4})", question.lower())
        if summary_match and df is not None:
            month_str = summary_match.group(1)
            year = int(summary_match.group(2))

            # Convert short month name to month number
            month_num = pd.to_datetime(month_str[:3], format="%b").month

            # Convert and filter
            df['date'] = pd.to_datetime(df['date'])
            filtered = df[(df['date'].dt.month == month_num) & (df['date'].dt.year == year)]

            if filtered.empty:
                return f"🔍 No data found for {month_str.capitalize()} {year}."

            total = filtered["amount"].sum()
            top_categories = filtered.groupby("category")["amount"].sum().sort_values(ascending=False).head(3)

            response = f"📊 **Summary for {month_str.capitalize()} {year}**\n"
            response += f"- Total expenses: ₹{total:.2f}\n"
            response += "- Top 3 categories:\n"
            for cat, amt in top_categories.items():
                response += f"  • {cat.title()}: ₹{amt:.2f}\n"

            return response

        # Otherwise: use LLM for generic queries like "how can I save money"
        return agent.run(question)

    except Exception as e:
        return f"⚠️ Sorry, I couldn't process that: {str(e)}"