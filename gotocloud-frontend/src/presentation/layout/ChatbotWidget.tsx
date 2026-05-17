import { useEffect, useRef, useState } from "react";
import { MdClose, MdSend } from "react-icons/md";
import { sendChatbotMessage } from "../../infrastructure/api/chatbot.api";
import CamilaImage from '../../shared/img/camila.jpeg';
import "./ChatbotWidget.css";

type ChatMessage = {
  id: string;
  role: "assistant" | "user";
  content: string;
};

type ChatbotWidgetProps = {
  onClose: () => void;
};

const initialMessages: ChatMessage[] = [
  {
    id: "welcome",
    role: "assistant",
    content:
      "Hola, soy Camila de GoToCloud. Puedo ayudarte con servicios cloud, productos SaaS, datos, seguridad o conectarte con un asesor.",
  },
];

function createMessage(role: ChatMessage["role"], content: string): ChatMessage {
  return {
    id: `${role}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    content,
  };
}

function ChatbotWidget({ onClose }: ChatbotWidgetProps) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [message, setMessage] = useState("");
  const [sessionId, setSessionId] = useState<string>();
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, sending]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const cleanMessage = message.trim();
    if (!cleanMessage || sending) return;

    setMessage("");
    setSending(true);
    setMessages((currentMessages) => [
      ...currentMessages,
      createMessage("user", cleanMessage),
    ]);

    try {
      const response = await sendChatbotMessage({
        message: cleanMessage,
        sessionId,
      });

      setSessionId(response.sessionId);
      setMessages((currentMessages) => [
        ...currentMessages,
        createMessage("assistant", response.reply),
      ]);
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : "No pude conectarme con el chatbot en este momento.";

      setMessages((currentMessages) => [
        ...currentMessages,
        createMessage("assistant", errorMessage),
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <section className="chatbot-widget" aria-label="Chatbot de GoToCloud">
      <header className="chatbot-widget__header">
        <div className="chatbot-widget__agent">
          <span className="chatbot-widget__avatar">
            <img className="chatbot-widget__img" src={CamilaImage} alt="Icono Camila Bot" />
          </span>
          <div>
            <strong>Camila</strong>
            <span>Agente IA de GoToCloud</span>
          </div>
        </div>

        <button
          className="chatbot-widget__close"
          type="button"
          aria-label="Cerrar chatbot"
          onClick={onClose}
        >
          <MdClose size={20} />
        </button>
      </header>

      <div className="chatbot-widget__messages" aria-live="polite">
        {messages.map((item) => (
          <div
            className={`chatbot-widget__message chatbot-widget__message--${item.role}`}
            key={item.id}
          >
            {item.content}
          </div>
        ))}

        {sending && (
          <div className="chatbot-widget__message chatbot-widget__message--assistant">
            Camila está escribiendo...
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="chatbot-widget__form" onSubmit={handleSubmit}>
        <label className="visually-hidden" htmlFor="chatbot-message">
          Mensaje para Camila
        </label>
        <input
          id="chatbot-message"
          type="text"
          value={message}
          placeholder="Escribe tu mensaje..."
          disabled={sending}
          onChange={(event) => setMessage(event.target.value)}
        />
        <button type="submit" aria-label="Enviar mensaje" disabled={sending || !message.trim()}>
          <MdSend size={20} />
        </button>
      </form>
    </section>
  );
}

export default ChatbotWidget;
