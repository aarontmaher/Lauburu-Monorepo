import axios from 'axios';

export interface DeviceProfile {
    platform?: 'ios' | 'android' | 'macos' | 'linux' | 'windows' | 'web';
    ramGb?: number;
    taskType?: 'chat' | 'code' | 'tool_call' | 'telemetry';
}

export interface EdgeModelConfig {
    id: string;
    name: string;
    endpoint: string;
    maxContextTokens: number;
    paramSize: string;
    ramFootprintGb: number;
    capabilities: string[];
}

interface ChatMessage {
    role: string;
    content: string;
}

export class EdgeAIChatRouter {
    // Local High-Speed Edge Inference Port (:8083)
    private static readonly EDGE_PORT =
        process.env.EDGE_AI_ENDPOINT || 'http://127.0.0.1:8083/v1/chat/completions';
    private static readonly LOCAL_FALLBACK_TIMEOUT_MS = 30000;

    // Strict <= 3B Multipurpose Edge Model Inventory
    private static readonly EDGE_MODELS: Record<string, EdgeModelConfig> = {
        SMOLLM2_1_7B: {
            id: 'smollm2-1.7b-instruct-q4_k_m',
            name: 'SmolLM2 1.7B Multipurpose Edge AI',
            endpoint: EdgeAIChatRouter.EDGE_PORT,
            maxContextTokens: 2048,
            paramSize: '1.7B',
            ramFootprintGb: 0.98,
            capabilities: ['Conversational Chat', 'UI Navigation', 'POSIX Shell', 'Fast Responses']
        },
        QWEN_CODER_3B: {
            id: 'qwen2.5-coder-3b-instruct-q4_k_m',
            name: 'Qwen 2.5 Coder 3B Multipurpose Edge AI',
            endpoint: EdgeAIChatRouter.EDGE_PORT,
            maxContextTokens: 4096,
            paramSize: '3.0B',
            ramFootprintGb: 1.96,
            capabilities: ['Code Synthesis', 'Git Diff Patching', 'Tool Calling', 'AST Refactor']
        },
        QWEN_CODER_1_5B: {
            id: 'qwen2.5-coder-1.5b-instruct-q4_k_m',
            name: 'Qwen 2.5 Coder 1.5B Multipurpose Edge SLM',
            endpoint: EdgeAIChatRouter.EDGE_PORT,
            maxContextTokens: 2048,
            paramSize: '1.5B',
            ramFootprintGb: 1.04,
            capabilities: ['Low-Overhead Chat', 'Telemetry Monitoring', 'Micro-Automation']
        }
    };

    private static readonly MULTIPURPOSE_SYSTEM_PROMPT = `You are the Lauburu Multipurpose Edge AI Assistant.
You run locally and directly on-device as a high-speed, lightweight edge model (<= 3B parameters).
You handle all tasks: conversational chat, code generation, tool calling, and telemetry analysis with zero latency.`;

    /**
     * Resolves the multipurpose edge model. NEVER escalates to 7B or higher.
     */
    public static resolveModelForDevice(device: DeviceProfile): EdgeModelConfig {
        const ram = device.ramGb || 4.0;
        const task = device.taskType || 'chat';

        // Strict Edge Invariant: Maximum model is 3B, minimum 1.5B.
        if (task === 'code' || task === 'tool_call') {
            return this.EDGE_MODELS.QWEN_CODER_3B;
        } else if (ram <= 2.0) {
            return this.EDGE_MODELS.QWEN_CODER_1_5B;
        } else {
            return this.EDGE_MODELS.SMOLLM2_1_7B;
        }
    }

    public static async generateResponse(
        messages: ChatMessage[],
        device: DeviceProfile
    ): Promise<{ text: string; model: EdgeModelConfig; latencyMs: number }> {
        const modelConfig = this.resolveModelForDevice(device);
        const t0 = Date.now();

        const formattedMessages = [
            { role: 'system', content: this.MULTIPURPOSE_SYSTEM_PROMPT },
            ...messages
        ];

        const payload = {
            model: modelConfig.id,
            messages: formattedMessages,
            temperature: 0.7,
            max_tokens: modelConfig.maxContextTokens
        };

        try {
            const response = await axios.post(modelConfig.endpoint, payload, { timeout: 8000 });
            return {
                text: this.extractCompletionText(response.data, modelConfig.name),
                model: modelConfig,
                latencyMs: Date.now() - t0
            };
        } catch (localError) {
            const fallbackConfig = this.getLocalFallbackConfig();

            const response = await axios.post(
                fallbackConfig.endpoint,
                {
                    ...payload,
                    model: fallbackConfig.id
                },
                {
                    timeout: this.LOCAL_FALLBACK_TIMEOUT_MS
                }
            );

            return {
                text: this.extractCompletionText(response.data, fallbackConfig.name),
                model: fallbackConfig,
                latencyMs: Date.now() - t0
            };
        }
    }

    private static getLocalFallbackConfig(): EdgeModelConfig {
        return {
            id:
                process.env.LOCAL_STRONG_FALLBACK_MODEL ||
                'qwen2.5-coder-7b-instruct-q4_k_m',
            name: 'Qwen 2.5 Coder 7B Local Fallback',
            endpoint:
                process.env.LOCAL_STRONG_FALLBACK_ENDPOINT ||
                'http://127.0.0.1:8083/v1/chat/completions',
            maxContextTokens: 4096,
            paramSize: '7.6B',
            ramFootprintGb: 4.7,
            capabilities: ['Local Fallback', 'Code Generation', 'Tool Calling']
        };
    }

    private static extractCompletionText(data: unknown, providerName: string): string {
        if (
            typeof data === 'object' &&
            data !== null &&
            'choices' in data &&
            Array.isArray(data.choices) &&
            typeof data.choices[0]?.message?.content === 'string'
        ) {
            return data.choices[0].message.content;
        }

        throw new Error(`${providerName} returned no chat completion content.`);
    }
}
