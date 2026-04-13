Qwen-ASR transcribes audio files to text with support for 26 languages, emotion detection, and word-level timestamps. This page covers request and response parameters for each connection type.

**Getting started:** For model details and selection guidance, see [Audio file recognition - Qwen](/help/en/model-studio/qwen-speech-recognition).

## Choose a connection type

Each model supports specific connection types for different use cases.

| **Model** | **Supported connection types** | **Best for** |
| --- | --- | --- |
| Qwen3-ASR-Flash | OpenAI compatible, DashScope synchronous | Real-time recognition of short audio (up to 10 MB) |
| Qwen3-ASR-Flash-Filetrans | DashScope asynchronous only | Long audio files or batch processing |

**Important**

US region: Use DashScope synchronous or asynchronous (OpenAI compatible mode not supported).

**Recommended:** Audio files under 10 MB → [OpenAI compatible](#d397bcc41eu3q) (Qwen3-ASR-Flash). Long audio files → [DashScope asynchronous](#9937e8884002q) (Qwen3-ASR-Flash-Filetrans).

* * *

## OpenAI compatible

### Endpoints

All examples use the OpenAI compatible endpoint (Qwen3-ASR-Flash).

| **Deployment mode** | **HTTP endpoint** | **SDK base\\_url** |
| --- | --- | --- |
| [International](/help/en/model-studio/regions/#080da663a75xh) (Singapore) | `POST https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions` | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` |
| [Chinese Mainland](/help/en/model-studio/regions/#080da663a75xh) (Beijing) | `POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions` | `https://dashscope.aliyuncs.com/compatible-mode/v1` |

-   **International:** Endpoint and data storage in Singapore. Global inference (excluding Chinese mainland).
    
-   **Chinese Mainland:** Endpoint and data storage in Beijing. Inference restricted to Chinese mainland.
    
-   API keys differ by region. See [Get API key](/help/en/model-studio/get-api-key).
    

### Request body

| **Parameter** | **Type** | **Required** | **Description** |
| --- | --- | --- | --- |
| `model` | string | Yes | The [model](/help/en/model-studio/qwen-speech-recognition#b8c8c0483153o) name. Set to `qwen3-asr-flash`. |
| `messages` | array | Yes | The message list. See [Message structure (OpenAI compatible)](#h4-f2cd0aba). |
| `asr_options` | object | No  | Recognition options (see [asr\\_options (OpenAI compatible)](#h4-b42ac308)). Not a standard OpenAI parameter—pass via `extra_body` in OpenAI SDKs. |
| `stream` | boolean | No  | Default: `false`. Set to `true` for faster first-token response and reduced timeout risk (see [Streaming output](/help/en/model-studio/stream)). |
| `stream_options` | object | No  | Streaming configuration. Only effective when `stream` is `true`. Do not set when `stream` is `false`. |
| `stream_options.include_usage` | boolean | No  | Default: `false`. When `true`, token usage appears in the last chunk of the streaming response. |

#### Message structure (OpenAI compatible)

**System message** (optional)

Provide background text for context biasing (entity vocabularies, domain terms, or reference info) to improve accuracy. Place it at the beginning of the messages array.

| **Property** | **Type** | **Required** | **Description** |
| --- | --- | --- | --- |
| `role` | string | Yes | Set to `system`. |
| `content` | array | Yes | One message element allowed. |
| `content[].text` | string | No  | Context text. 10,000-token limit. See [Context biasing](/help/en/model-studio/qwen-speech-recognition#33fdf0438d5jd). |

**User message** (required)

| **Property** | **Type** | **Required** | **Description** |
| --- | --- | --- | --- |
| `role` | string | Yes | Set to `user`. |
| `content` | array | Yes | One message element allowed. |
| `content[].type` | string | Yes | Set to `input_audio`. |
| `content[].input_audio.data` | string | Yes | Audio input. Accepts a publicly accessible URL or a Base64-encoded [Data URL](https://www.rfc-editor.org/rfc/rfc2397). See [Audio input formats](#h3-c4e172ca). |

#### asr\_options (OpenAI compatible)

| **Parameter** | **Type** | **Required** | **Description** |
| --- | --- | --- | --- |
| `language` | string | No  | No default. Specify audio language to improve accuracy (one language per request). Omit for multilingual audio (e.g., mixed Chinese, English, Japanese, Korean). See [Supported languages](#h2-5234e940). |
| `enable_itn` | boolean | No  | Default: `false`. Enable Inverse Text Normalization (ITN) to convert spoken forms to written forms (e.g., "one hundred" → "100"). Chinese and English only. |

### Audio input formats

Qwen3-ASR-Flash in OpenAI compatible mode accepts two input formats:

-   **URL:** A publicly accessible audio file URL.
    
-   **Base64-encoded Data URL:** Format: `data:<mediatype>;base64,<data>`. Common MIME types: `audio/wav` (WAV), `audio/mpeg` (MP3). Base64 encoding increases file size—keep original file small enough to stay within 10 MB limit.
    

**OSS URL restrictions:**

-   **SDK calls:** Cannot use temporary `oss://` prefix URLs. Use standard HTTP URLs.
    
-   **RESTful API calls:** Can use `oss://` prefix URLs, but note:
    

**Important**

-   Temporary upload URLs expire after 48 hours—do not use in production.
    
-   Upload credential API: 100 QPS limit (no scale-out). Do not use in production, high-concurrency, or stress testing.
    
-   For production, store audio in [Object Storage Service (OSS)](/help/en/oss/user-guide/what-is-oss) for reliable, long-term availability.
    

### Sample code

All examples send an audio file URL to Qwen3-ASR-Flash using the OpenAI compatible endpoint.

Replace the endpoint and API key for your region before running. Set `DASHSCOPE_API_KEY` environment variable or replace `os.getenv("DASHSCOPE_API_KEY")` with your key.

#### Input: audio file URL

##### Python

```
from openai import OpenAI
import os

try:
    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        # International (Singapore). Beijing: https://dashscope.aliyuncs.com/compatible-mode/v1
        base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    )

    stream_enabled = False
    completion = client.chat.completions.create(
        model="qwen3-asr-flash",
        messages=[
            {
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": "https://dashscope.oss-cn-beijing.aliyuncs.com/audios/welcome.mp3"
                        }
                    }
                ],
                "role": "user"
            }
        ],
        stream=stream_enabled,
        extra_body={
            "asr_options": {
                # "language": "zh",
                "enable_itn": False
            }
        }
    )
    if stream_enabled:
        full_content = ""
        for chunk in completion:
            # When stream_options.include_usage is True, the last chunk has an empty choices list
            if chunk.choices and chunk.choices[0].delta.content:
                full_content += chunk.choices[0].delta.content
        print(f"Result: {full_content}")
    else:
        print(f"Result: {completion.choices[0].message.content}")
except Exception as e:
    print(f"Error: {e}")
```

##### Node.js

```
import OpenAI from "openai";

const client = new OpenAI({
  apiKey: process.env.DASHSCOPE_API_KEY,
  // International (Singapore). Beijing: https://dashscope.aliyuncs.com/compatible-mode/v1
  baseURL: "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
});

async function main() {
  try {
    const streamEnabled = false;
    const completion = await client.chat.completions.create({
      model: "qwen3-asr-flash",
      messages: [
        {
          role: "user",
          content: [
            {
              type: "input_audio",
              input_audio: {
                data: "https://dashscope.oss-cn-beijing.aliyuncs.com/audios/welcome.mp3"
              }
            }
          ]
        }
      ],
      stream: streamEnabled,
      extra_body: {
        asr_options: {
          // language: "zh",
          enable_itn: false
        }
      }
    });

    if (streamEnabled) {
      let fullContent = "";
      for await (const chunk of completion) {
        if (chunk.choices && chunk.choices.length > 0) {
          const delta = chunk.choices[0].delta;
          if (delta && delta.content) {
            fullContent += delta.content;
          }
        }
      }
      console.log(`Result: ${fullContent}`);
    } else {
      console.log(`Result: ${completion.choices[0].message.content}`);
    }
  } catch (err) {
    console.error(`Error: ${err}`);
  }
}

main();
```

##### cURL

Use the `text` field in the system message to provide context for custom recognition.

```
curl -X POST 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions' \
-H "Authorization: Bearer $DASHSCOPE_API_KEY" \
-H "Content-Type: application/json" \
-d '{
    "model": "qwen3-asr-flash",
    "messages": [
        {
            "content": [
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": "https://dashscope.oss-cn-beijing.aliyuncs.com/audios/welcome.mp3"
                    }
                }
            ],
            "role": "user"
        }
    ],
    "stream": false,
    "asr_options": {
        "enable_itn": false
    }
}'
```

#### Input: Base64-encoded audio file

Encode local audio file as Base64 Data URL before sending: `data:<mediatype>;base64,<data>`.

**Encoding examples:**

Python:

```
import base64, pathlib

file_path = pathlib.Path("input.mp3")
base64_str = base64.b64encode(file_path.read_bytes()).decode()
data_uri = f"data:audio/mpeg;base64,{base64_str}"
```

Java:

```
import java.nio.file.*;
import java.util.Base64;

public class Main {
    public static String toDataUrl(String filePath) throws Exception {
        byte[] bytes = Files.readAllBytes(Paths.get(filePath));
        String encoded = Base64.getEncoder().encodeToString(bytes);
        return "data:audio/mpeg;base64," + encoded;
    }

    public static void main(String[] args) throws Exception {
        System.out.println(toDataUrl("input.mp3"));
    }
}
```

After encoding, pass the `data_uri` as the `input_audio.data` value. The following examples use the sample file [welcome.mp3](https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/en-US/20260106/gpkfrr/welcome.mp3).

##### Python

```
import base64
from openai import OpenAI
import os
import pathlib

try:
    # Replace with the path and MIME type of your audio file
    file_path = "welcome.mp3"
    audio_mime_type = "audio/mpeg"

    file_path_obj = pathlib.Path(file_path)
    if not file_path_obj.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    base64_str = base64.b64encode(file_path_obj.read_bytes()).decode()
    data_uri = f"data:{audio_mime_type};base64,{base64_str}"

    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        # International (Singapore). Beijing: https://dashscope.aliyuncs.com/compatible-mode/v1
        base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    )

    stream_enabled = False
    completion = client.chat.completions.create(
        model="qwen3-asr-flash",
        messages=[
            {
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": data_uri
                        }
                    }
                ],
                "role": "user"
            }
        ],
        stream=stream_enabled,
        extra_body={
            "asr_options": {
                # "language": "zh",
                "enable_itn": False
            }
        }
    )
    if stream_enabled:
        full_content = ""
        for chunk in completion:
            if chunk.choices and chunk.choices[0].delta.content:
                full_content += chunk.choices[0].delta.content
        print(f"Result: {full_content}")
    else:
        print(f"Result: {completion.choices[0].message.content}")
except Exception as e:
    print(f"Error: {e}")
```

##### Node.js

```
import OpenAI from "openai";
import { readFileSync } from 'fs';

const client = new OpenAI({
  apiKey: process.env.DASHSCOPE_API_KEY,
  // International (Singapore). Beijing: https://dashscope.aliyuncs.com/compatible-mode/v1
  baseURL: "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
});

const encodeAudioFile = (audioFilePath) => {
    const audioFile = readFileSync(audioFilePath);
    return audioFile.toString('base64');
};

// Replace with the path to your audio file
const dataUri = `data:audio/mpeg;base64,${encodeAudioFile("welcome.mp3")}`;

async function main() {
  try {
    const streamEnabled = false;
    const completion = await client.chat.completions.create({
      model: "qwen3-asr-flash",
      messages: [
        {
          role: "user",
          content: [
            {
              type: "input_audio",
              input_audio: {
                data: dataUri
              }
            }
          ]
        }
      ],
      stream: streamEnabled,
      extra_body: {
        asr_options: {
          // language: "zh",
          enable_itn: false
        }
      }
    });

    if (streamEnabled) {
      let fullContent = "";
      for await (const chunk of completion) {
        if (chunk.choices && chunk.choices.length > 0) {
          const delta = chunk.choices[0].delta;
          if (delta && delta.content) {
            fullContent += delta.content;
          }
        }
      }
      console.log(`Result: ${fullContent}`);
    } else {
      console.log(`Result: ${completion.choices[0].message.content}`);
    }
  } catch (err) {
    console.error(`Error: ${err}`);
  }
}

main();
```

### Response body

| **Field** | **Type** | **Description** |
| --- | --- | --- |
| `id` | string | Unique identifier for this request. |
| `model` | string | Model used for this request. |
| `object` | string | Always `chat.completion`. |
| `created` | integer | UNIX timestamp (seconds) when the request was created. |
| `choices` | array | Model output. See [choices fields (OpenAI compatible)](#h4-c233a19b). |
| `usage` | object | Token consumption. See [usage fields (OpenAI compatible)](#h4-18a80d0c). |

#### choices fields (OpenAI compatible)

| **Field** | **Type** | **Description** |
| --- | --- | --- |
| `index` | integer | Position in the `choices` array. |
| `finish_reason` | string | `null`: generation in progress. `stop`: finished naturally. `length`: output exceeded maximum length. |
| `message.role` | string | Always `assistant`. |
| `message.content` | string | The transcribed text. |
| `message.annotations` | array | Metadata about the recognized audio. |
| `message.annotations[].type` | string | Always `audio_info`. |
| `message.annotations[].language` | string | Detected language code. If `language` was specified in the request, this matches that value. See [Supported languages](#h2-5234e940). |
| `message.annotations[].emotion` | string | Detected emotion: `surprised`, `neutral`, `happy`, `sad`, `disgusted`, `angry`, or `fearful`. |

#### usage fields (OpenAI compatible)

| **Field** | **Type** | **Description** |
| --- | --- | --- |
| `prompt_tokens` | integer | Total input tokens. |
| `prompt_tokens_details.audio_tokens` | integer | Audio input tokens. Each second = 25 tokens. Audio shorter than 1 second counts as 1 second. |
| `prompt_tokens_details.text_tokens` | integer | Ignore this field. |
| `completion_tokens` | integer | Output tokens. |
| `completion_tokens_details.text_tokens` | integer | Output text tokens. |
| `seconds` | integer | Audio duration in seconds. |
| `total_tokens` | integer | `prompt_tokens` + `completion_tokens`. |

### Response examples

#### Non-streaming output

```
{
    "choices": [
        {
            "finish_reason": "stop",
            "index": 0,
            "message": {
                "annotations": [
                    {
                        "emotion": "neutral",
                        "language": "zh",
                        "type": "audio_info"
                    }
                ],
                "content": "Welcome to Alibaba Cloud.",
                "role": "assistant"
            }
        }
    ],
    "created": 1767683986,
    "id": "chatcmpl-487abe5f-d4f2-9363-a877-xxxxxxx",
    "model": "qwen3-asr-flash",
    "object": "chat.completion",
    "usage": {
        "completion_tokens": 12,
        "completion_tokens_details": {
            "text_tokens": 12
        },
        "prompt_tokens": 42,
        "prompt_tokens_details": {
            "audio_tokens": 42,
            "text_tokens": 0
        },
        "seconds": 1,
        "total_tokens": 54
    }
}
```

#### Streaming output

```
data: {"model":"qwen3-asr-flash","id":"chatcmpl-3fb97803-d27f-9289-8889-xxxxx","created":1767685989,"object":"chat.completion.chunk","usage":null,"choices":[{"logprobs":null,"index":0,"delta":{"content":"","role":"assistant"}}]}

data: {"model":"qwen3-asr-flash","id":"chatcmpl-3fb97803-d27f-9289-8889-xxxxx","choices":[{"delta":{"annotations":[{"type":"audio_info","language":"zh","emotion":"neutral"}],"content":"Welcome","role":null},"index":0}],"created":1767685989,"object":"chat.completion.chunk","usage":null}

data: {"model":"qwen3-asr-flash","id":"chatcmpl-3fb97803-d27f-9289-8889-xxxxx","choices":[{"delta":{"annotations":[{"type":"audio_info","language":"zh","emotion":"neutral"}],"content":" to","role":null},"index":0}],"created":1767685989,"object":"chat.completion.chunk","usage":null}

data: {"model":"qwen3-asr-flash","id":"chatcmpl-3fb97803-d27f-9289-8889-xxxxx","choices":[{"delta":{"annotations":[{"type":"audio_info","language":"zh","emotion":"neutral"}],"content":" Alibaba","role":null},"index":0}],"created":1767685989,"object":"chat.completion.chunk","usage":null}

data: {"model":"qwen3-asr-flash","id":"chatcmpl-3fb97803-d27f-9289-8889-xxxxx","choices":[{"delta":{"annotations":[{"type":"audio_info","language":"zh","emotion":"neutral"}],"content":" Cloud","role":null},"index":0}],"created":1767685989,"object":"chat.completion.chunk","usage":null}

data: {"model":"qwen3-asr-flash","id":"chatcmpl-3fb97803-d27f-9289-8889-xxxxx","choices":[{"delta":{"annotations":[{"type":"audio_info","language":"zh","emotion":"neutral"}],"content":".","role":null},"index":0}],"created":1767685989,"object":"chat.completion.chunk","usage":null}

data: {"model":"qwen3-asr-flash","id":"chatcmpl-3fb97803-d27f-9289-8889-xxxxx","choices":[{"delta":{"role":null},"index":0,"finish_reason":"stop"}],"created":1767685989,"object":"chat.completion.chunk","usage":null}

data: [DONE]
```

* * *

## DashScope synchronous

### Endpoints

| **Deployment mode** | **HTTP endpoint** | **SDK base\\_url** |
| --- | --- | --- |
| [International](/help/en/model-studio/regions/#080da663a75xh) (Singapore) | `POST https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation` | `https://dashscope-intl.aliyuncs.com/api/v1` |
| [US](/help/en/model-studio/regions/#080da663a75xh) (Virginia) | `POST https://dashscope-us.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation` | `https://dashscope-us.aliyuncs.com/api/v1` |
| [Chinese Mainland](/help/en/model-studio/regions/#080da663a75xh) (Beijing) | `POST https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation` | `https://dashscope.aliyuncs.com/api/v1` |

-   **International:** Endpoint and data storage in Singapore. Global inference (excluding Chinese mainland).
    
-   **US:** Endpoint and data storage in Virginia. Inference restricted to United States.
    
-   **Chinese Mainland:** Endpoint and data storage in Beijing. Inference restricted to Chinese mainland.
    
-   US region models: Append `-us` to model name (e.g., `qwen3-asr-flash-us`).
    

### Request body

| **Parameter** | **Type** | **Required** | **Description** |
| --- | --- | --- | --- |
| `model` | string | Yes | The [model](/help/en/model-studio/qwen-speech-recognition#b8c8c0483153o) name. Set to `qwen3-asr-flash`. For the US region, use `qwen3-asr-flash-us`. |
| `messages` | array | Yes | Message list. Place inside `input` object for HTTP calls (see [Message structure (DashScope synchronous)](#h4-7490f860)). |
| `asr_options` | object | No  | Recognition options. Place inside `parameters` for HTTP calls. See [asr\\_options (DashScope synchronous)](#h4-64fbc387). Supported by Qwen3-ASR-Flash only. |

#### Message structure (DashScope synchronous)

**System message** (optional, Qwen3-ASR-Flash only)

Provide context for customized recognition. Place it at the beginning of the messages array.

| **Property** | **Type** | **Required** | **Description** |
| --- | --- | --- | --- |
| `role` | string | Yes | Set to `system`. |
| `content` | array | Yes | One message element allowed. |
| `content[].text` | string | No  | Context text. 10,000-token limit. See [Context biasing](/help/en/model-studio/qwen-speech-recognition#33fdf0438d5jd). |

**User message** (required)

| **Property** | **Type** | **Required** | **Description** |
| --- | --- | --- | --- |
| `role` | string | Yes | Set to `user`. |
| `content` | array | Yes | One message element allowed. |
| `content[].audio` | string | Yes | Audio to recognize. Accepts Base64-encoded files, absolute paths of local files, or publicly accessible URLs. See [Audio input formats](#h3-c4e172ca) for OSS URL restrictions. For getting started examples, see [QuickStart](/help/en/model-studio/qwen-speech-recognition#7818a3bc466d6). |

#### asr\_options (DashScope synchronous)

Same parameters as [asr\_options (OpenAI compatible)](#h4-b42ac308): `language` and `enable_itn`.

### Sample code

The following examples recognize audio from a URL. For local audio file examples, see [QuickStart](/help/en/model-studio/qwen-speech-recognition#7818a3bc466d6).

#### cURL

```
curl -X POST "https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation" \
-H "Authorization: Bearer $DASHSCOPE_API_KEY" \
-H "Content-Type: application/json" \
-d '{
    "model": "qwen3-asr-flash",
    "input": {
        "messages": [
            {
                "content": [
                    {
                        "text": ""
                    }
                ],
                "role": "system"
            },
            {
                "content": [
                    {
                        "audio": "https://dashscope.oss-cn-beijing.aliyuncs.com/audios/welcome.mp3"
                    }
                ],
                "role": "user"
            }
        ]
    },
    "parameters": {
        "asr_options": {
            "enable_itn": false
        }
    }
}'
```

#### Java

```
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

import com.alibaba.dashscope.aigc.multimodalconversation.MultiModalConversation;
import com.alibaba.dashscope.aigc.multimodalconversation.MultiModalConversationParam;
import com.alibaba.dashscope.aigc.multimodalconversation.MultiModalConversationResult;
import com.alibaba.dashscope.common.MultiModalMessage;
import com.alibaba.dashscope.common.Role;
import com.alibaba.dashscope.exception.ApiException;
import com.alibaba.dashscope.exception.NoApiKeyException;
import com.alibaba.dashscope.exception.UploadFileException;
import com.alibaba.dashscope.utils.Constants;
import com.alibaba.dashscope.utils.JsonUtils;

public class Main {
    public static void simpleMultiModalConversationCall()
            throws ApiException, NoApiKeyException, UploadFileException {
        MultiModalConversation conv = new MultiModalConversation();
        MultiModalMessage userMessage = MultiModalMessage.builder()
                .role(Role.USER.getValue())
                .content(Arrays.asList(
                        Collections.singletonMap("audio", "https://dashscope.oss-cn-beijing.aliyuncs.com/audios/welcome.mp3")))
                .build();

        MultiModalMessage sysMessage = MultiModalMessage.builder().role(Role.SYSTEM.getValue())
                .content(Arrays.asList(Collections.singletonMap("text", "")))
                .build();

        Map<String, Object> asrOptions = new HashMap<>();
        asrOptions.put("enable_itn", false);
        // asrOptions.put("language", "zh");
        MultiModalConversationParam param = MultiModalConversationParam.builder()
                .apiKey(System.getenv("DASHSCOPE_API_KEY"))
                // US region: use "qwen3-asr-flash-us"
                .model("qwen3-asr-flash")
                .message(sysMessage)
                .message(userMessage)
                .parameter("asr_options", asrOptions)
                .build();
        MultiModalConversationResult result = conv.call(param);
        System.out.println(JsonUtils.toJson(result));
    }
    public static void main(String[] args) {
        try {
            // International (Singapore). Beijing: https://dashscope.aliyuncs.com/api/v1
            // US: https://dashscope-us.aliyuncs.com/api/v1
            Constants.baseHttpApiUrl = "https://dashscope-intl.aliyuncs.com/api/v1";
            simpleMultiModalConversationCall();
        } catch (ApiException | NoApiKeyException | UploadFileException e) {
            System.out.println(e.getMessage());
        }
        System.exit(0);
    }
}
```

#### Python

```
import os
import dashscope

# International (Singapore). Beijing: https://dashscope.aliyuncs.com/api/v1
# US: https://dashscope-us.aliyuncs.com/api/v1
dashscope.base_http_api_url = 'https://dashscope-intl.aliyuncs.com/api/v1'

messages = [
    {"role": "system", "content": [{"text": ""}]},
    {"role": "user", "content": [{"audio": "https://dashscope.oss-cn-beijing.aliyuncs.com/audios/welcome.mp3"}]}
]

response = dashscope.MultiModalConversation.call(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    # US region: use "qwen3-asr-flash-us"
    model="qwen3-asr-flash",
    messages=messages,
    result_format="message",
    asr_options={
        #"language": "zh",
        "enable_itn": False
    }
)
print(response)
```

### Response body

| **Field** | **Type** | **Description** |
| --- | --- | --- |
| `request_id` | string | Unique identifier for this request. The Java SDK returns this as `requestId`. |
| `output.choices` | array | Model output. Returned when `result_format` is `message`. |
| `output.choices[].finish_reason` | string | `null`: generation in progress. `stop`: finished naturally. `length`: output exceeded maximum length. |
| `output.choices[].message.role` | string | Always `assistant`. |
| `output.choices[].message.content[].text` | string | The transcribed text. |
| `output.choices[].message.annotations` | array | Audio metadata. Same structure as [choices fields (OpenAI compatible)](#h4-c233a19b): `type`, `language`, `emotion`. |
| `usage.input_tokens_details.text_tokens` | integer | Ignore this field. |
| `usage.output_tokens_details.text_tokens` | integer | Output text token count. |
| `usage.seconds` | integer | Audio duration in seconds. |

### Response example

```
{
    "output": {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "annotations": [
                        {
                            "language": "zh",
                            "type": "audio_info",
                            "emotion": "neutral"
                        }
                    ],
                    "content": [
                        {
                            "text": "Welcome to Alibaba Cloud."
                        }
                    ],
                    "role": "assistant"
                }
            }
        ]
    },
    "usage": {
        "input_tokens_details": {
            "text_tokens": 0
        },
        "output_tokens_details": {
            "text_tokens": 6
        },
        "seconds": 1
    },
    "request_id": "568e2bf0-d6f2-97f8-9f15-a57b11dc6977"
}
```

* * *

## DashScope asynchronous

Use asynchronous mode (Qwen3-ASR-Flash-Filetrans) for long audio files or batch processing. Uses submit-poll workflow to avoid timeouts.

### How it works

1.  **Submit task:** Send audio file URL. Server validates and returns `task_id`.
    
2.  **Poll for result:** Query result endpoint with `task_id` until status is `SUCCEEDED`.
    

**SDK vs. RESTful API:**

| **Approach** | **Submit** | **Poll** |
| --- | --- | --- |
| **SDK** | Call `async_call()` (Python) or `asyncCall()` (Java). Returns task object with `task_id`. | Call `fetch()` with the task object. The SDK handles polling automatically. |
| **RESTful API** | POST to the submit endpoint. Parse `task_id` from the response. | GET the result endpoint with `task_id`. Implement polling logic manually. |

For SDK examples, see [Getting started](/help/en/model-studio/qwen-speech-recognition#7818a3bc466d6).

### Step 1: Submit a task

#### Endpoints

| **Deployment mode** | **HTTP endpoint** | **SDK base\\_url** |
| --- | --- | --- |
| [International](/help/en/model-studio/regions/#080da663a75xh) (Singapore) | `POST https://dashscope-intl.aliyuncs.com/api/v1/services/audio/asr/transcription` | `https://dashscope-intl.aliyuncs.com/api/v1` |
| [Chinese Mainland](/help/en/model-studio/regions/#080da663a75xh) (Beijing) | `POST https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription` | `https://dashscope.aliyuncs.com/api/v1` |

#### Request body

| **Parameter** | **Type** | **Required** | **Description** |
| --- | --- | --- | --- |
| `model` | string | Yes | Set to `qwen3-asr-flash-filetrans`. |
| `input.file_url` | string | Yes | Publicly accessible URL of the audio file. See [Audio input formats](#h3-c4e172ca) for OSS URL restrictions. |
| `parameters.language` | string | No  | No default. Audio language hint. See [Supported languages](#h2-5234e940). |
| `parameters.enable_itn` | boolean | No  | Default: `false`. Enable Inverse Text Normalization (ITN). Chinese and English only. |
| `parameters.enable_words` | boolean | No  | Default: `false`. Returns word-level timestamps. When `true`, sentence segmentation uses VAD and punctuation; when `false`, VAD only. Supported languages: Chinese, English, Japanese, Korean, German, French, Spanish, Italian, Portuguese, Russian. |
| `parameters.text` | string | No  | Context text for biasing. 10,000-token limit. See [Context biasing](/help/en/model-studio/qwen-speech-recognition#33fdf0438d5jd). |
| `parameters.channel_id` | array | No  | Default: `[0]`. Audio track indexes to recognize in multi-channel audio (index starts from 0). Example: `[0, 1]` recognizes first two tracks. |

**Important**

Each audio track is billed separately. Example: `[0, 1]` incurs two charges.

#### Sample code

##### cURL

```
curl --location --request POST 'https://dashscope-intl.aliyuncs.com/api/v1/services/audio/asr/transcription' \
--header "Authorization: Bearer $DASHSCOPE_API_KEY" \
--header "Content-Type: application/json" \
--header "X-DashScope-Async: enable" \
--data '{
    "model": "qwen3-asr-flash-filetrans",
    "input": {
        "file_url": "https://dashscope.oss-cn-beijing.aliyuncs.com/audios/welcome.mp3"
    },
    "parameters": {
        "channel_id": [0],
        "enable_itn": false
    }
}'
```

##### Java

For SDK examples, see [Getting started](/help/en/model-studio/qwen-speech-recognition#7818a3bc466d6).

```
import com.google.gson.Gson;
import com.google.gson.annotations.SerializedName;
import okhttp3.*;

import java.io.IOException;

public class Main {
    // International (Singapore). Beijing: https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription
    private static final String API_URL = "https://dashscope-intl.aliyuncs.com/api/v1/services/audio/asr/transcription";

    public static void main(String[] args) {
        String apiKey = System.getenv("DASHSCOPE_API_KEY");

        OkHttpClient client = new OkHttpClient();
        Gson gson = new Gson();

        String payloadJson = """
                {
                    "model": "qwen3-asr-flash-filetrans",
                    "input": {
                        "file_url": "https://dashscope.oss-cn-beijing.aliyuncs.com/audios/welcome.mp3"
                    },
                    "parameters": {
                        "channel_id": [0],
                        "enable_itn": false
                    }
                }
                """;

        RequestBody body = RequestBody.create(payloadJson, MediaType.get("application/json; charset=utf-8"));
        Request request = new Request.Builder()
                .url(API_URL)
                .addHeader("Authorization", "Bearer " + apiKey)
                .addHeader("Content-Type", "application/json")
                .addHeader("X-DashScope-Async", "enable")
                .post(body)
                .build();

        try (Response response = client.newCall(request).execute()) {
            if (response.isSuccessful() && response.body() != null) {
                String respBody = response.body().string();
                ApiResponse apiResp = gson.fromJson(respBody, ApiResponse.class);
                if (apiResp.output != null) {
                    System.out.println("task_id: " + apiResp.output.taskId);
                } else {
                    System.out.println(respBody);
                }
            } else {
                System.out.println("Task failed. HTTP code: " + response.code());
                if (response.body() != null) {
                    System.out.println(response.body().string());
                }
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    static class ApiResponse {
        @SerializedName("request_id")
        String requestId;

        Output output;
    }

    static class Output {
        @SerializedName("task_id")
        String taskId;

        @SerializedName("task_status")
        String taskStatus;
    }
}
```

##### Python

For SDK examples, see [Getting started](/help/en/model-studio/qwen-speech-recognition#7818a3bc466d6).

```
import requests
import json
import os

# International (Singapore). Beijing: https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription
url = "https://dashscope-intl.aliyuncs.com/api/v1/services/audio/asr/transcription"

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

headers = {
    "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
    "Content-Type": "application/json",
    "X-DashScope-Async": "enable"
}

payload = {
    "model": "qwen3-asr-flash-filetrans",
    "input": {
        "file_url": "https://dashscope.oss-cn-beijing.aliyuncs.com/audios/welcome.mp3"
    },
    "parameters": {
        "channel_id": [0],
        # "language": "zh",
        "enable_itn": False
    }
}

response = requests.post(url, headers=headers, data=json.dumps(payload))
if response.status_code == 200:
    print(f"task_id: {response.json()['output']['task_id']}")
else:
    print("Task failed.")
    print(response.json())
```

#### Response body

```
{
    "request_id": "92e3decd-0c69-47a8-************",
    "output": {
        "task_id": "8fab76d0-0eed-4d20-************",
        "task_status": "PENDING"
    }
}
```

| **Field** | **Type** | **Description** |
| --- | --- | --- |
| `request_id` | string | Unique identifier for this request. |
| `output.task_id` | string | Task ID. Use this to poll for results. |
| `output.task_status` | string | Task status: `PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`, or `UNKNOWN`. |

### Step 2: Get the result

#### Endpoints

| **Deployment mode** | **HTTP endpoint** | **SDK base\\_url** |
| --- | --- | --- |
| International (Singapore) | `GET https://dashscope-intl.aliyuncs.com/api/v1/tasks/{task_id}` | `https://dashscope-intl.aliyuncs.com/api/v1` |
| Chinese Mainland (Beijing) | `GET https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}` | `https://dashscope.aliyuncs.com/api/v1` |

Replace `{task_id}` with `task_id` from Step 1.

#### Sample code

##### cURL

```
curl --location --request GET 'https://dashscope-intl.aliyuncs.com/api/v1/tasks/{task_id}' \
--header "Authorization: Bearer $DASHSCOPE_API_KEY" \
--header "X-DashScope-Async: enable" \
--header "Content-Type: application/json"
```

##### Java

For SDK examples, see [Getting started](/help/en/model-studio/qwen-speech-recognition#7818a3bc466d6).

```
import okhttp3.*;

import java.io.IOException;

public class Main {
    public static void main(String[] args) {
        String taskId = "<your-task-id>";
        String apiKey = System.getenv("DASHSCOPE_API_KEY");

        // International (Singapore). Beijing: https://dashscope.aliyuncs.com/api/v1/tasks/
        String apiUrl = "https://dashscope-intl.aliyuncs.com/api/v1/tasks/" + taskId;

        OkHttpClient client = new OkHttpClient();

        Request request = new Request.Builder()
                .url(apiUrl)
                .addHeader("Authorization", "Bearer " + apiKey)
                .addHeader("X-DashScope-Async", "enable")
                .addHeader("Content-Type", "application/json")
                .get()
                .build();

        try (Response response = client.newCall(request).execute()) {
            if (response.body() != null) {
                System.out.println(response.body().string());
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
```

##### Python

For SDK examples, see [Getting started](/help/en/model-studio/qwen-speech-recognition#7818a3bc466d6).

```
import os
import requests

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

task_id = "<your-task-id>"
# International (Singapore). Beijing: https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}
url = f"https://dashscope-intl.aliyuncs.com/api/v1/tasks/{task_id}"

headers = {
    "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
    "X-DashScope-Async": "enable",
    "Content-Type": "application/json"
}

response = requests.get(url, headers=headers)
print(response.json())
```

#### Response body

| **Field** | **Type** | **Description** |
| --- | --- | --- |
| `request_id` | string | Unique identifier for this request. |
| `output.task_id` | string | Task ID. |
| `output.task_status` | string | `PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`, or `UNKNOWN` (task does not exist). |
| `output.result.transcription_url` | string | Download URL for transcription result JSON file (valid 24 hours). See [Transcription result format](#h3-59e03ecf). |
| `output.submit_time` | string | Task submission time. |
| `output.scheduled_time` | string | Task execution start time. |
| `output.end_time` | string | Task completion time. |
| `output.task_metrics.TOTAL` | integer | Total subtask count. |
| `output.task_metrics.SUCCEEDED` | integer | Successful subtask count. |
| `output.task_metrics.FAILED` | integer | Failed subtask count. |
| `output.code` | string | Error code. Returned only on failure. |
| `output.message` | string | Error message. Returned only on failure. |
| `usage.seconds` | integer | Audio duration in seconds. |

#### Response examples

## RUNNING

```
{
    "request_id": "6769df07-2768-4fb0-ad59-************",
    "output": {
        "task_id": "9be1700a-0f8e-4778-be74-************",
        "task_status": "RUNNING",
        "submit_time": "2025-10-27 14:19:31.150",
        "scheduled_time": "2025-10-27 14:19:31.233",
        "task_metrics": {
            "TOTAL": 1,
            "SUCCEEDED": 0,
            "FAILED": 0
        }
    }
}
```

## SUCCEEDED

```
{
    "request_id": "1dca6c0a-0ed1-4662-aa39-************",
    "output": {
        "task_id": "8fab76d0-0eed-4d20-929f-************",
        "task_status": "SUCCEEDED",
        "submit_time": "2025-10-27 13:57:45.948",
        "scheduled_time": "2025-10-27 13:57:46.018",
        "end_time": "2025-10-27 13:57:47.079",
        "result": {
            "transcription_url": "http://dashscope-result-bj.oss-cn-beijing.aliyuncs.com/..."
        }
    },
    "usage": {
        "seconds": 3
    }
}
```

## FAILED

```
{
    "request_id": "3d141841-858a-466a-9ff9-************",
    "output": {
        "task_id": "c58c7951-7789-4557-9ea3-************",
        "task_status": "FAILED",
        "submit_time": "2025-10-27 15:06:06.915",
        "scheduled_time": "2025-10-27 15:06:06.967",
        "end_time": "2025-10-27 15:06:07.584",
        "code": "FILE_403_FORBIDDEN",
        "message": "FILE_403_FORBIDDEN"
    }
}
```

### Transcription result format

`transcription_url` returns a JSON file with complete results. Download or read via HTTP GET (expires after 24 hours).

```
{
    "file_url": "https://***.wav",
    "audio_info": {
        "format": "wav",
        "sample_rate": 16000
    },
    "transcripts": [
        {
            "channel_id": 0,
            "text": "Senior staff, Principal Doris Jackson, Wakefield faculty, and of course my fellow classmates. I am honored to have been chosen to speak before my classmates along with the students across America today.",
            "sentences": [
                {
                    "sentence_id": 0,
                    "begin_time": 240,
                    "end_time": 6720,
                    "language": "en",
                    "emotion": "happy",
                    "text": "Senior staff, Principal Doris Jackson, Wakefield faculty, and of course my fellow classmates.",
                    "words": [
                        {
                            "begin_time": 240,
                            "end_time": 1120,
                            "text": "Senior ",
                            "punctuation": ""
                        },
                        {
                            "begin_time": 1120,
                            "end_time": 1200,
                            "text": "staff",
                            "punctuation": ","
                        }
                    ]
                }
            ]
        }
    ]
}
```

| **Field** | **Type** | **Description** |
| --- | --- | --- |
| `file_url` | string | URL of the recognized audio file. |
| `audio_info.format` | string | Audio format (for example, `wav`, `mp3`). |
| `audio_info.sample_rate` | integer | Audio sampling rate in Hz. |
| `transcripts` | array | Recognition results, one element per audio track. |
| `transcripts[].channel_id` | integer | Audio track index, starting from 0. |
| `transcripts[].text` | string | Full transcribed text for this track. |
| `transcripts[].sentences` | array | Sentence-level results. |
| `transcripts[].sentences[].sentence_id` | integer | Sentence index, starting from 0. |
| `transcripts[].sentences[].begin_time` | integer | Sentence start timestamp in milliseconds. |
| `transcripts[].sentences[].end_time` | integer | Sentence end timestamp in milliseconds. |
| `transcripts[].sentences[].text` | string | Transcribed text for this sentence. |
| `transcripts[].sentences[].language` | string | Detected language code. See [Supported languages](#h2-5234e940). |
| `transcripts[].sentences[].emotion` | string | Detected emotion: `surprised`, `neutral`, `happy`, `sad`, `disgusted`, `angry`, or `fearful`. |
| `transcripts[].sentences[].words` | array | Word-level results. Returned only when `enable_words` is `true`. |
| `transcripts[].sentences[].words[].begin_time` | integer | Word start timestamp in milliseconds. |
| `transcripts[].sentences[].words[].end_time` | integer | Word end timestamp in milliseconds. |
| `transcripts[].sentences[].words[].text` | string | Recognized word. |
| `transcripts[].sentences[].words[].punctuation` | string | Punctuation mark following this word. |

* * *

## Supported languages

Specify a language code in `language` to improve accuracy. Omit for multilingual audio.

| **Code** | **Language** |
| --- | --- |
| `zh` | Chinese (Mandarin, Sichuanese, Minnan, and Wu) |
| `yue` | Cantonese |
| `en` | English |
| `ja` | Japanese |
| `de` | German |
| `ko` | Korean |
| `ru` | Russian |
| `fr` | French |
| `pt` | Portuguese |
| `ar` | Arabic |
| `it` | Italian |
| `es` | Spanish |
| `hi` | Hindi |
| `id` | Indonesian |
| `th` | Thai |
| `tr` | Turkish |
| `uk` | Ukrainian |
| `vi` | Vietnamese |
| `cs` | Czech |
| `da` | Danish |
| `fil` | Filipino |
| `fi` | Finnish |
| `is` | Icelandic |
| `ms` | Malay |
| `no` | Norwegian |
| `pl` | Polish |
| `sv` | Swedish |