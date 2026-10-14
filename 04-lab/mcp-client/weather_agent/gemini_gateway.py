"""Use complete Gemini responses on gateways where streamed tool continuation fails."""
from google.adk.models import Gemini


class GatewayGemini(Gemini):
    async def generate_content_async(self, llm_request, stream=False):
        # ADK still streams events to the browser; only provider token streaming is disabled.
        async for response in super().generate_content_async(llm_request, stream=False):
            yield response
