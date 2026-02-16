import { useState, useRef, useEffect } from 'react';

interface ChatMessage { id: string; role: 'user' | 'assistant'; content: string; }
const QUICK_PROMPTS = ["How does screenplay conversion work?", "What video formats?", "AI scene generation", "Pricing plans", "Export options", "API access"];

export function AIChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; }, [messages]);

  const handleSend = (text?: string) => {
    const msg = text || input.trim();
    if (!msg || isLoading) return;
    setMessages(prev => [...prev, { id: `u-${Date.now()}`, role: 'user', content: msg }]);
    setInput('');
    setIsLoading(true);
    setTimeout(() => {
      setMessages(prev => [...prev, { id: `a-${Date.now()}`, role: 'assistant', content: getResponse(msg) }]);
      setIsLoading(false);
    }, 500);
  };

  if (!isOpen) return (
    <button onClick={() => setIsOpen(true)} className="fixed bottom-6 right-6 w-14 h-14 rounded-full bg-gradient-to-r from-amber-500 to-red-500 text-white shadow-lg z-50 flex items-center justify-center hover:scale-105 transition-transform">
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" /></svg>
    </button>
  );

  return (
    <div className="fixed bottom-6 right-6 w-96 h-[500px] bg-white rounded-2xl shadow-2xl flex flex-col z-50 border overflow-hidden">
      <div className="p-4 bg-gradient-to-r from-amber-500 to-red-500 text-white flex justify-between items-center">
        <div><h3 className="font-semibold">SceneMachine Support</h3><p className="text-sm opacity-90">Screenplay to movie help</p></div>
        <button onClick={() => setIsOpen(false)} className="hover:bg-white/20 p-1 rounded"><svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg></button>
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50">
        {messages.length === 0 && (
          <div className="text-center py-4">
            <p className="text-gray-600 mb-4">How can I help with SceneMachine?</p>
            <div className="flex flex-wrap gap-2 justify-center">
              {QUICK_PROMPTS.map((p, i) => (<button key={i} onClick={() => handleSend(p)} className="px-3 py-1 text-sm bg-white border rounded-full hover:border-amber-400">{p}</button>))}
            </div>
          </div>
        )}
        {messages.map(m => (
          <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] px-4 py-2 rounded-2xl whitespace-pre-line ${m.role === 'user' ? 'bg-amber-500 text-white' : 'bg-white border shadow-sm'}`}>{m.content}</div>
          </div>
        ))}
        {isLoading && <div className="flex justify-start"><div className="bg-white border px-4 py-2 rounded-2xl shadow-sm">Typing...</div></div>}
      </div>
      <div className="p-4 border-t bg-white">
        <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} className="flex gap-2">
          <input value={input} onChange={e => setInput(e.target.value)} placeholder="Ask about movies..." className="flex-1 px-4 py-2 border rounded-full focus:outline-none focus:border-amber-400" />
          <button type="submit" disabled={isLoading || !input.trim()} className="w-10 h-10 rounded-full bg-gradient-to-r from-amber-500 to-red-500 text-white disabled:opacity-50 flex items-center justify-center">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>
          </button>
        </form>
      </div>
    </div>
  );
}

function getResponse(q: string): string {
  const question = q.toLowerCase();
  if (question.includes('screenplay') || question.includes('convert') || question.includes('work')) return "SceneMachine transforms written screenplays into generated videos:\n1. Upload screenplay (.fdx, .fountain, .pdf)\n2. AI parses scenes, characters, dialogue\n3. Generate storyboards and shot lists\n4. Render video with AI actors and scenes";
  if (question.includes('format') || question.includes('video')) return "Output formats:\n• MP4 (H.264, H.265)\n• MOV (ProRes)\n• WebM\n• Resolution: 720p to 4K\n• Aspect: 16:9, 9:16, 1:1, 2.35:1";
  if (question.includes('scene') || question.includes('ai') || question.includes('generat')) return "AI Scene Generation:\n• Character synthesis from descriptions\n• Location generation (indoor, outdoor, any setting)\n• Lighting and mood control\n• Camera movement simulation\n• VFX and transitions";
  if (question.includes('price') || question.includes('pricing') || question.includes('plan')) return "Plans:\n• Free: 5 min/month, watermarked\n• Creator ($49/mo): 60 min/month, no watermark\n• Studio ($199/mo): Unlimited, 4K, API\n• Enterprise: Custom rendering, priority";
  if (question.includes('export')) return "Export options:\n• Video file download\n• Frame-by-frame storyboard\n• Shot list document\n• Script breakdown\n• Direct upload to YouTube/Vimeo";
  if (question.includes('api')) return "API on Studio+ plans:\n• Batch screenplay processing\n• Webhook notifications\n• Custom render settings\n• Asset management";
  return "I can help with: screenplay conversion, video formats, AI generation, pricing, export, or API. What would you like to know?";
}

export default AIChatWidget;
