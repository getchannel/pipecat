#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#
#

import base64
import io
import json
from enum import Enum
from typing import List, Literal, Optional

from loguru import logger
from PIL import Image
from pydantic import BaseModel, Field

from pipecat.frames.frames import ImageRawFrame

#
# Client events
#


class MediaChunk(BaseModel):
    mimeType: str
    data: str


class ContentPart(BaseModel):
    text: Optional[str] = Field(default=None, validate_default=False)
    inlineData: Optional[MediaChunk] = Field(default=None, validate_default=False)
    fileData: Optional['FileData'] = Field(default=None, validate_default=False)


class FileData(BaseModel):
    """Represents a file reference in the Gemini File API."""
    mimeType: str
    fileUri: str


ContentPart.model_rebuild()  # Rebuild model to resolve forward reference


class Turn(BaseModel):
    role: Literal["user", "model"] = "user"
    parts: List[ContentPart]


class StartSensitivity(str, Enum):
    """Determines how start of speech is detected."""

    UNSPECIFIED = "START_SENSITIVITY_UNSPECIFIED"  # Default is HIGH
    HIGH = "START_SENSITIVITY_HIGH"  # Detect start of speech more often
    LOW = "START_SENSITIVITY_LOW"  # Detect start of speech less often


class EndSensitivity(str, Enum):
    """Determines how end of speech is detected."""

    UNSPECIFIED = "END_SENSITIVITY_UNSPECIFIED"  # Default is HIGH
    HIGH = "END_SENSITIVITY_HIGH"  # End speech more often
    LOW = "END_SENSITIVITY_LOW"  # End speech less often


class AutomaticActivityDetection(BaseModel):
    """Configures automatic detection of activity."""

    disabled: Optional[bool] = None
    start_of_speech_sensitivity: Optional[StartSensitivity] = None
    prefix_padding_ms: Optional[int] = None
    end_of_speech_sensitivity: Optional[EndSensitivity] = None
    silence_duration_ms: Optional[int] = None


class RealtimeInputConfig(BaseModel):
    """Configures the realtime input behavior."""

    automatic_activity_detection: Optional[AutomaticActivityDetection] = None


class RealtimeInput(BaseModel):
    mediaChunks: List[MediaChunk]


class ClientContent(BaseModel):
    turns: Optional[List[Turn]] = None
    turnComplete: bool = False


class AudioInputMessage(BaseModel):
    realtimeInput: RealtimeInput

    @classmethod
    def from_raw_audio(cls, raw_audio: bytes, sample_rate: int) -> "AudioInputMessage":
        data = base64.b64encode(raw_audio).decode("utf-8")
        return cls(
            realtimeInput=RealtimeInput(
                mediaChunks=[MediaChunk(mimeType=f"audio/pcm;rate={sample_rate}", data=data)]
            )
        )


class VideoInputMessage(BaseModel):
    realtimeInput: RealtimeInput

    @classmethod
    def from_image_frame(cls, frame: ImageRawFrame) -> "VideoInputMessage":
        buffer = io.BytesIO()
        Image.frombytes(frame.format, frame.size, frame.image).save(buffer, format="JPEG")
        data = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return cls(
            realtimeInput=RealtimeInput(mediaChunks=[MediaChunk(mimeType=f"image/jpeg", data=data)])
        )


class ClientContentMessage(BaseModel):
    clientContent: ClientContent


class SystemInstruction(BaseModel):
    parts: List[ContentPart]


class AudioTranscriptionConfig(BaseModel):
    pass


class Setup(BaseModel):
    model: str
    system_instruction: Optional[SystemInstruction] = None
    tools: Optional[List[dict]] = None
    generation_config: Optional[dict] = None
    input_audio_transcription: Optional[AudioTranscriptionConfig] = None
    output_audio_transcription: Optional[AudioTranscriptionConfig] = None
    realtime_input_config: Optional[RealtimeInputConfig] = None


class Config(BaseModel):
    setup: Setup


#
# Grounding metadata models
#


class SearchEntryPoint(BaseModel):
    """Represents the search entry point with rendered content for search suggestions."""
    renderedContent: Optional[str] = None


class WebSource(BaseModel):
    """Represents a web source from grounding chunks."""
    uri: Optional[str] = None
    title: Optional[str] = None


class GroundingChunk(BaseModel):
    """Represents a grounding chunk containing web source information."""
    web: Optional[WebSource] = None


class GroundingSegment(BaseModel):
    """Represents a segment of text that is grounded."""
    startIndex: Optional[int] = None
    endIndex: Optional[int] = None
    text: Optional[str] = None


class GroundingSupport(BaseModel):
    """Represents support information for grounded text segments."""
    segment: Optional[GroundingSegment] = None
    groundingChunkIndices: Optional[List[int]] = None
    confidenceScores: Optional[List[float]] = None


class GroundingMetadata(BaseModel):
    """Represents grounding metadata from Google Search."""
    searchEntryPoint: Optional[SearchEntryPoint] = None
    groundingChunks: Optional[List[GroundingChunk]] = None
    groundingSupports: Optional[List[GroundingSupport]] = None
    webSearchQueries: Optional[List[str]] = None


#
# Server events
#


class SetupComplete(BaseModel):
    pass


class InlineData(BaseModel):
    mimeType: str
    data: str


class Part(BaseModel):
    inlineData: Optional[InlineData] = None
    text: Optional[str] = None


class ModelTurn(BaseModel):
    parts: List[Part]


class ServerContentInterrupted(BaseModel):
    interrupted: bool


class ServerContentTurnComplete(BaseModel):
    turnComplete: bool


class BidiGenerateContentTranscription(BaseModel):
    text: str


class ServerContent(BaseModel):
    modelTurn: Optional[ModelTurn] = None
    interrupted: Optional[bool] = None
    turnComplete: Optional[bool] = None
    inputTranscription: Optional[BidiGenerateContentTranscription] = None
    outputTranscription: Optional[BidiGenerateContentTranscription] = None
    groundingMetadata: Optional[GroundingMetadata] = None


class FunctionCall(BaseModel):
    id: str
    name: str
    args: dict


class ToolCall(BaseModel):
    functionCalls: List[FunctionCall]


class Modality(str, Enum):
    """Modality types in token counts."""

    UNSPECIFIED = "MODALITY_UNSPECIFIED"
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"


class ModalityTokenCount(BaseModel):
    """Token count for a specific modality."""

    modality: Modality
    tokenCount: int


class UsageMetadata(BaseModel):
    """Usage metadata about the response."""

    promptTokenCount: Optional[int] = None
    cachedContentTokenCount: Optional[int] = None
    responseTokenCount: Optional[int] = None
    toolUsePromptTokenCount: Optional[int] = None
    thoughtsTokenCount: Optional[int] = None
    totalTokenCount: Optional[int] = None
    promptTokensDetails: Optional[List[ModalityTokenCount]] = None
    cacheTokensDetails: Optional[List[ModalityTokenCount]] = None
    responseTokensDetails: Optional[List[ModalityTokenCount]] = None
    toolUsePromptTokensDetails: Optional[List[ModalityTokenCount]] = None


class ServerEvent(BaseModel):
    setupComplete: Optional[SetupComplete] = None
    serverContent: Optional[ServerContent] = None
    toolCall: Optional[ToolCall] = None
    usageMetadata: Optional[UsageMetadata] = None


def parse_server_event(message_str):
    from loguru import logger  # Import logger locally to avoid scoping issues
    
    try:
        evt_dict = json.loads(message_str)
        
        # Only log grounding metadata detection if truly needed for debugging
        # In production, this could be removed entirely or moved to TRACE level
        if 'serverContent' in evt_dict:
            server_content = evt_dict['serverContent']
            if 'groundingMetadata' in server_content:
                # Consider removing this log entirely for production
                pass

        evt = ServerEvent.model_validate(evt_dict)
        return evt
    except Exception as e:
        logger.error(f"Error parsing server event: {e}")
        # Truncate raw message to avoid logging potentially sensitive or overly long data
        truncated_message = message_str[:200] + "..." if len(message_str) > 200 else message_str
        logger.error(f"Raw message (truncated): {truncated_message}")
        return None


class ContextWindowCompressionConfig(BaseModel):
    """Configuration for context window compression."""

    sliding_window: Optional[bool] = Field(default=True)
    trigger_tokens: Optional[int] = Field(default=None)
