import { useState, useRef, useEffect } from 'react';
import { MessageSquare, X, Send } from 'lucide-react';

export default function ChatbotWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<{sender: 'bot' | 'user', text: string}[]>([
    { sender: 'bot', text: 'Merhaba! Ben Agro Chatbot. Bitki bakımı, tahlil sonuçları veya tarım planlama hakkında aklınıza takılanları sorabilirsiniz.' }
  ]);
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Otomatik aşağı kaydırma
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (!input.trim()) return;
    
    // Kullanıcı mesajı ekle
    setMessages(prev => [...prev, { sender: 'user', text: input }]);
    setInput('');

    // Mock Bot Yanıtı (Normalde Backend /ai/chat vs endpointine gider)
    setTimeout(() => {
      setMessages(prev => [...prev, { 
        sender: 'bot', 
        text: 'Anlıyorum. Külleme hastalığı için sistemin önerdiği kükürt dozunu güneş tam tepedeyken UYGULAMAYINIZ, yaprakları yakabilir. Akşam üstünü tercih etmelisiniz.' 
      }]);
    }, 1500);
  };

  return (
    <>
      {/* Bot Balonu (Kapalıysa görünür) */}
      {!isOpen && (
        <button 
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 bg-green-600 text-white p-4 rounded-full shadow-2xl hover:bg-green-700 transition transform hover:scale-110 z-50 flex items-center justify-center"
        >
          <MessageSquare size={28} />
        </button>
      )}

      {/* Chat Açık Pencere */}
      {isOpen && (
        <div className="fixed bottom-6 right-6 w-96 bg-white rounded-3xl shadow-2xl border border-earth-200 flex flex-col overflow-hidden z-50 h-[500px]">
          
          {/* Header */}
          <div className="bg-green-600 text-white p-4 flex justify-between items-center">
            <div className="flex flex-col">
               <span className="font-bold text-lg">Agro Uzman Asistan</span>
               <span className="text-xs text-green-200">🤖 Çevrimiçi</span>
            </div>
            <button onClick={() => setIsOpen(false)} className="text-green-50 hover:text-white">
              <X size={24} />
            </button>
          </div>

          {/* Mesaj Listesi */}
          <div className="flex-1 p-4 overflow-y-auto bg-earth-50 flex flex-col gap-3">
             {messages.map((msg, idx) => (
               <div key={idx} className={`max-w-[85%] rounded-2xl p-3 text-sm ${
                 msg.sender === 'user' 
                   ? 'bg-green-600 text-white self-end rounded-tr-none' 
                   : 'bg-white text-earth-800 border border-earth-200 self-start rounded-tl-none shadow-sm'
               }`}>
                 {msg.text}
               </div>
             ))}
             <div ref={messagesEndRef} />
          </div>

          {/* Giriş Alanı */}
          <div className="p-3 bg-white border-t border-earth-200 flex gap-2">
             <input 
               type="text" 
               value={input}
               onChange={(e) => setInput(e.target.value)}
               onKeyDown={(e) => e.key === 'Enter' && handleSend()}
               placeholder="Soru yazın..."
               className="flex-1 bg-earth-100 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-green-500 text-sm"
             />
             <button 
               onClick={handleSend}
               className="bg-green-600 text-white p-3 rounded-xl hover:bg-green-700 transition"
             >
               <Send size={20} />
             </button>
          </div>
        </div>
      )}
    </>
  );
}
