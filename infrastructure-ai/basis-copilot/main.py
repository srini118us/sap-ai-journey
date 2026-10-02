from agent import sap_basis_agent

if __name__ == "__main__":
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    import asyncio

    async def main():
        session_service = InMemorySessionService()
        runner = Runner(
            agent=sap_basis_agent,
            app_name="sap_basis_copilot",
            session_service=session_service
        )
        print("SAP Basis Copilot is ready!")
        print("Starting web UI...")

    asyncio.run(main())
