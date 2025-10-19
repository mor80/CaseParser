import { useEffect, useMemo, useState } from "react";
import {
  FaArrowUp,
  FaBox,
  FaChartArea,
  FaChartBar,
  FaChartLine,
  FaChartPie,
  FaDoorOpen,
  FaPlus,
  FaSignInAlt,
  FaTable,
  FaUserCircle,
} from "react-icons/fa";
import { clsx } from "clsx";

const API_BASE_URL =
  (typeof import.meta !== "undefined" && import.meta.env.VITE_API_BASE_URL) ||
  "http://localhost:8000";

type Section = "dashboard" | "cases" | "analytics" | "portfolio";

type MarketOverview = {
  total_cases: number;
  cases_with_statistics: number;
  average_price: number;
  gainers_24h: number;
  losers_24h: number;
  last_update: string | null;
  market_sentiment: string;
};

type TopMover = {
  case_id: string;
  name: string;
  current_price: number;
  price_change: number;
  last_updated: string;
};

type VolatileCase = {
  case_id: string;
  name: string;
  volatility: number;
  avg_price: number;
  min_price: number;
  max_price: number;
  price_range: number;
};

type SimpleCase = {
  id: string;
  name: string;
  steam_url?: string | null;
  created_at: string;
  updated_at: string;
  latest_price?: number | null;
  latest_price_timestamp?: string | null;
  price_change_24h?: number | null;
  price_change_7d?: number | null;
  price_change_30d?: number | null;
  min_price_30d?: number | null;
  max_price_30d?: number | null;
  avg_price_30d?: number | null;
};

type PortfolioEntry = {
  id: string;
  case_id: string;
  case_name: string;
  quantity: number;
  purchase_price: number;
  purchase_date: string;
  current_price?: number | null;
  current_price_timestamp?: string | null;
  total_investment: number;
  current_value: number;
  profit: number;
  profit_percentage: number;
  notes?: string | null;
};

type PortfolioStats = {
  total_investment: number;
  current_value: number;
  total_profit: number;
  profit_percentage: number;
  total_cases: number;
  last_updated: string;
};

type User = {
  id: string;
  email: string;
  username: string;
  created_at: string;
  updated_at: string;
};

type AuthMode = "login" | "register";

interface AuthModalState {
  open: boolean;
  mode: AuthMode;
  error?: string;
}

const sentimentLabel: Record<string, { text: string; icon: string; color: string }> =
  {
    bullish: { text: "Бычий рынок", icon: "↑", color: "#22c55e" },
    bearish: { text: "Медвежий рынок", icon: "↓", color: "#ef4444" },
    neutral: { text: "Нейтральный", icon: "→", color: "#facc15" },
  };

const formatCurrency = (value?: number | null) =>
  typeof value === "number" ? `${value.toFixed(2)} ₽` : "—";

const formatPercent = (value?: number | null) =>
  typeof value === "number" ? `${value >= 0 ? "+" : ""}${value.toFixed(2)}%` : "—";

const formatDateTime = (value?: string | null) =>
  value ? new Date(value).toLocaleString() : "—";

async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null
): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    const message =
      detail?.detail || response.statusText || "Произошла неизвестная ошибка";
    throw new Error(message);
  }
  return response.json();
}

const App = () => {
  const [section, setSection] = useState<Section>("dashboard");
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);

  const [marketOverview, setMarketOverview] = useState<MarketOverview | null>(null);
  const [topGainers, setTopGainers] = useState<TopMover[]>([]);
  const [topLosers, setTopLosers] = useState<TopMover[]>([]);
  const [volatileCases, setVolatileCases] = useState<VolatileCase[]>([]);
  const [cases, setCases] = useState<SimpleCase[]>([]);
  const [portfolioEntries, setPortfolioEntries] = useState<PortfolioEntry[]>([]);
  const [portfolioStats, setPortfolioStats] = useState<PortfolioStats | null>(null);

  const [loading, setLoading] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);

  const [authModal, setAuthModal] = useState<AuthModalState>({
    open: false,
    mode: "login",
  });

  const loadUser = async (authToken: string) => {
    try {
      const current = await apiRequest<User>("/auth/me", {}, authToken);
      setUser(current);
    } catch (error) {
      console.error(error);
      setToken(null);
      setUser(null);
      localStorage.removeItem("caseparser_token");
    }
  };

  useEffect(() => {
    const existingToken = localStorage.getItem("caseparser_token");
    if (existingToken) {
      setToken(existingToken);
      loadUser(existingToken);
    }
  }, []);

  const refreshInterval = useMemo(() => {
    return setInterval(() => {
      if (section === "dashboard") {
        void loadDashboardData();
      } else if (section === "cases") {
        void loadCasesData();
      } else if (section === "analytics") {
        void loadAnalyticsData();
      } else if (section === "portfolio") {
        void loadPortfolioData();
      }
    }, 5 * 60 * 1000);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [section, token]);

  useEffect(() => {
    return () => clearInterval(refreshInterval);
  }, [refreshInterval]);

  useEffect(() => {
    if (section === "dashboard") {
      void loadDashboardData();
    } else if (section === "cases") {
      void loadCasesData();
    } else if (section === "analytics") {
      void loadAnalyticsData();
    } else if (section === "portfolio" && token) {
      void loadPortfolioData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [section, token]);

  const loadDashboardData = async () => {
    setLoading(true);
    setGlobalError(null);
    try {
      const [overview, gainers, losers, volatility] = await Promise.all([
        apiRequest<MarketOverview>("/analytics/market-overview"),
        apiRequest<TopMover[]>("/analytics/top-gainers?days=7&limit=5"),
        apiRequest<TopMover[]>("/analytics/top-losers?days=7&limit=5"),
        apiRequest<VolatileCase[]>("/analytics/volatile-cases?days=30&limit=5"),
      ]);
      setMarketOverview(overview);
      setTopGainers(gainers);
      setTopLosers(losers);
      setVolatileCases(volatility);
    } catch (error) {
      console.error(error);
      setGlobalError((error as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const loadCasesData = async () => {
    setLoading(true);
    setGlobalError(null);
    try {
      const allCases = await apiRequest<SimpleCase[]>("/cases");
      setCases(allCases);
    } catch (error) {
      console.error(error);
      setGlobalError((error as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const loadAnalyticsData = async () => {
    setLoading(true);
    setGlobalError(null);
    try {
      const [volatility, overview] = await Promise.all([
        apiRequest<VolatileCase[]>("/analytics/volatile-cases?days=30&limit=10"),
        apiRequest<MarketOverview>("/analytics/market-overview"),
      ]);
      setVolatileCases(volatility);
      setMarketOverview(overview);
    } catch (error) {
      console.error(error);
      setGlobalError((error as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const loadPortfolioData = async () => {
    if (!token) {
      setAuthModal({ open: true, mode: "login" });
      return;
    }
    setLoading(true);
    setGlobalError(null);
    try {
      const [stats, entries] = await Promise.all([
        apiRequest<PortfolioStats>("/portfolio/statistics", {}, token),
        apiRequest<PortfolioEntry[]>("/portfolio", {}, token),
      ]);
      setPortfolioStats(stats);
      setPortfolioEntries(entries);
    } catch (error) {
      console.error(error);
      setGlobalError((error as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    setToken(null);
    setUser(null);
    setPortfolioEntries([]);
    setPortfolioStats(null);
    localStorage.removeItem("caseparser_token");
  };

  const openAuthModal = (mode: AuthMode) => setAuthModal({ open: true, mode });

  const closeAuthModal = () => setAuthModal({ open: false, mode: "login" });

  const handleAuthSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const email = String(formData.get("email") || "").trim();
    const password = String(formData.get("password") || "").trim();
    const username = String(formData.get("username") || "").trim();

    if (!email || !password || (authModal.mode === "register" && !username)) {
      setAuthModal((prev) => ({ ...prev, error: "Заполните все поля" }));
      return;
    }

    try {
      const payload =
        authModal.mode === "login"
          ? { email, password }
          : { email, password, username };

      const endpoint = authModal.mode === "login" ? "/auth/login" : "/auth/register";
      const response = await apiRequest<{ access_token: string; user: User }>(
        endpoint,
        {
          method: "POST",
          body: JSON.stringify(payload),
        }
      );
      setToken(response.access_token);
      setUser(response.user);
      localStorage.setItem("caseparser_token", response.access_token);
      setAuthModal({ open: false, mode: "login" });
      if (section === "portfolio") {
        await loadPortfolioData();
      }
    } catch (error) {
      setAuthModal((prev) => ({
        ...prev,
        error: (error as Error).message,
      }));
    }
  };

  const handleAddToPortfolio = async (caseItem: SimpleCase) => {
    if (!token) {
      openAuthModal("login");
      return;
    }
    const quantity = prompt(
      `Введите количество для кейса "${caseItem.name}":`,
      "1"
    );
    const purchasePrice = prompt(
      `Введите цену покупки (за штуку) для кейса "${caseItem.name}":`,
      caseItem.latest_price?.toString() ?? "0"
    );
    if (!quantity || !purchasePrice) return;
    const parsedQuantity = Number(quantity);
    const parsedPrice = Number(purchasePrice);
    if (Number.isNaN(parsedQuantity) || Number.isNaN(parsedPrice)) {
      alert("Некорректные значения");
      return;
    }
    try {
      await apiRequest("/portfolio/add", {
        method: "POST",
        body: JSON.stringify({
          case_id: caseItem.id,
          quantity: parsedQuantity,
          purchase_price: parsedPrice,
        }),
      }, token);
      alert("Кейс добавлен в портфель");
      await loadPortfolioData();
    } catch (error) {
      alert((error as Error).message);
    }
  };

  const handleRemovePortfolioEntry = async (entryId: string) => {
    if (!token) return;
    if (!confirm("Удалить позицию из портфеля?")) return;
    try {
      await apiRequest(`/portfolio/${entryId}`, { method: "DELETE" }, token);
      setPortfolioEntries((prev) => prev.filter((entry) => entry.id !== entryId));
      await loadPortfolioData();
    } catch (error) {
      alert((error as Error).message);
    }
  };

  const handleSectionChange = (next: Section) => {
    setSection(next);
    setGlobalError(null);
  };

  const renderDashboard = () => (
    <>
      <div className="grid grid-cards">
        <StatCard
          icon={<FaBox size={28} />}
          label="Всего кейсов"
          value={marketOverview?.total_cases ?? "—"}
          accent="primary"
        />
        <StatCard
          icon={<FaArrowUp size={28} />}
          label="Средняя цена"
          value={formatCurrency(marketOverview?.average_price)}
          accent="info"
        />
        <StatCard
          icon={<FaChartLine size={28} />}
          label="Рост за 24ч"
          value={marketOverview?.gainers_24h ?? 0}
          accent="success"
        />
        <StatCard
          icon={<FaChartBar size={28} />}
          label="Падение за 24ч"
          value={marketOverview?.losers_24h ?? 0}
          accent="warning"
        />
      </div>

      <div className="card chart-card mt-lg">
        <div className="card-header">
          <h5 className="card-title">
            <FaChartArea className="me-sm" />
            График цен
          </h5>
        </div>
        <div className="card-body">
          <p className="text-muted">
            Для просмотра индивидуальных графиков откройте детали кейса.
          </p>
        </div>
      </div>

      <div className="grid grid-two mt-lg">
        <TopList title="Топ гейнеры" items={topGainers} tone="success" />
        <TopList title="Топ лузеры" items={topLosers} tone="danger" />
      </div>
    </>
  );

  const renderCases = () => (
    <div className="card mt-lg">
      <div className="card-header flex-between">
        <h5 className="card-title">
          <FaTable className="me-sm" />
          Все кейсы
        </h5>
        <input
          aria-label="Поиск кейсов"
          className="input search-input"
          placeholder="Поиск..."
          onChange={(event) => {
            const value = event.target.value.toLowerCase();
            const filtered = cases.filter((item) =>
              item.name.toLowerCase().includes(value)
            );
            setCases(filtered);
            if (!value) {
              void loadCasesData();
            }
          }}
        />
      </div>
      <div className="card-body">
        <div className="table-responsive">
          <table className="table">
            <thead>
              <tr>
                <th>Название</th>
                <th>Цена</th>
                <th>24ч</th>
                <th>7д</th>
                <th>30д</th>
                <th>Мин/Макс 30д</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {cases.length === 0 && (
                <tr>
                  <td colSpan={7} className="text-center text-muted py-lg">
                    Нет данных
                  </td>
                </tr>
              )}
              {cases.map((item) => (
                <tr key={item.id}>
                  <td>
                    <div className="case-name">
                      <strong>{item.name}</strong>
                      {item.steam_url && (
                        <a
                          href={item.steam_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-muted d-block small"
                        >
                          Ссылка Steam
                        </a>
                      )}
                    </div>
                  </td>
                  <td>
                    <div>{formatCurrency(item.latest_price)}</div>
                    <small className="text-muted">
                      {formatDateTime(item.latest_price_timestamp)}
                    </small>
                  </td>
                  <td className={clsx("text-strong", getChangeClass(item.price_change_24h))}>
                    {formatPercent(item.price_change_24h)}
                  </td>
                  <td className={clsx("text-strong", getChangeClass(item.price_change_7d))}>
                    {formatPercent(item.price_change_7d)}
                  </td>
                  <td className={clsx("text-strong", getChangeClass(item.price_change_30d))}>
                    {formatPercent(item.price_change_30d)}
                  </td>
                  <td>
                    <div>{formatCurrency(item.min_price_30d)}</div>
                    <div>{formatCurrency(item.max_price_30d)}</div>
                  </td>
                  <td>
                    <div className="btn-group">
                      <button
                        className="btn btn-outline-primary"
                        onClick={() => handleAddToPortfolio(item)}
                      >
                        <FaPlus /> В портфель
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );

  const renderAnalytics = () => (
    <div className="grid grid-two mt-lg">
      <div className="card">
        <div className="card-header">
          <h5 className="card-title">
            <FaChartPie className="me-sm" />
            Волатильные кейсы
          </h5>
        </div>
        <div className="card-body">
          {volatileCases.length === 0 ? (
            <div className="empty-state">Нет данных</div>
          ) : (
            <ul className="list-unstyled">
              {volatileCases.map((item) => (
                <li key={item.case_id} className="list-item">
                  <div>
                    <strong>{item.name}</strong>
                    <div className="text-muted small">
                      {formatCurrency(item.min_price)} — {formatCurrency(item.max_price)}
                    </div>
                  </div>
                  <div className="badge">
                    Волатильность: {item.volatility.toFixed(2)}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
      <div className="card">
        <div className="card-header">
          <h5 className="card-title">
            <FaChartLine className="me-sm" />
            Настроение рынка
          </h5>
        </div>
        <div className="card-body sentiment">
          <SentimentWidget overview={marketOverview} />
          <p className="text-muted mt-sm">На основе анализа за 24 часа</p>
        </div>
      </div>
    </div>
  );

  const renderPortfolio = () => (
    <>
      <div className="grid grid-four mt-lg">
        <StatCard
          icon={<FaChartLine size={28} />}
          label="Инвестиции"
          value={formatCurrency(portfolioStats?.total_investment)}
          accent="primary"
        />
        <StatCard
          icon={<FaArrowUp size={28} />}
          label="Текущая стоимость"
          value={formatCurrency(portfolioStats?.current_value)}
          accent="info"
        />
        <StatCard
          icon={<FaChartArea size={28} />}
          label="Прибыль"
          value={formatCurrency(portfolioStats?.total_profit)}
          accent="success"
        />
        <StatCard
          icon={<FaBox size={28} />}
          label="Всего кейсов"
          value={portfolioStats?.total_cases ?? "—"}
          accent="warning"
        />
      </div>
      <div className="grid grid-two mt-lg">
        <div className="card">
          <div className="card-header">
            <h5 className="card-title">
              <FaChartBar className="me-sm" />
              Состав портфеля
            </h5>
          </div>
          <div className="card-body">
            <div className="table-responsive">
              <table className="table">
                <thead>
                  <tr>
                    <th>Кейс</th>
                    <th>Кол-во</th>
                    <th>Покупка</th>
                    <th>Текущая цена</th>
                    <th>Прибыль</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {portfolioEntries.length === 0 && (
                    <tr>
                      <td colSpan={6} className="text-center text-muted py-lg">
                        Портфель пуст
                      </td>
                    </tr>
                  )}
                  {portfolioEntries.map((entry) => (
                    <tr key={entry.id}>
                      <td>
                        <strong>{entry.case_name}</strong>
                        <div className="text-muted small">
                          Покупка: {formatDateTime(entry.purchase_date)}
                        </div>
                        {entry.notes && (
                          <div className="text-muted small">{entry.notes}</div>
                        )}
                      </td>
                      <td>{entry.quantity.toFixed(2)}</td>
                      <td>
                        {formatCurrency(entry.purchase_price)}
                        <div className="text-muted small">
                          {formatCurrency(entry.total_investment)}
                        </div>
                      </td>
                      <td>
                        {formatCurrency(entry.current_price)}
                        <div className="text-muted small">
                          {formatDateTime(entry.current_price_timestamp)}
                        </div>
                      </td>
                      <td className={clsx("text-strong", getChangeClass(entry.profit))}>
                        {formatCurrency(entry.profit)}
                        <div className="text-muted small">
                          {formatPercent(entry.profit_percentage)}
                        </div>
                      </td>
                      <td>
                        <button
                          className="btn btn-outline-primary"
                          onClick={() => handleRemovePortfolioEntry(entry.id)}
                        >
                          Удалить
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="card-header">
            <h5 className="card-title">
              <FaUserCircle className="me-sm" />
              Подсказки
            </h5>
          </div>
          <div className="card-body">
            <p className="text-muted">
              Чтобы добавлять кейсы в портфель, авторизуйтесь и используйте кнопку
              «Добавить» в списке кейсов.
            </p>
            <p className="text-muted">
              После добавления позиции вы сможете контролировать прибыль и долю в
              портфеле в режиме реального времени.
            </p>
          </div>
        </div>
      </div>
    </>
  );

  return (
    <div>
      <nav className="navbar">
        <div className="navbar-inner">
          <div className="navbar-left">
            <span className="brand">
              <FaChartLine className="brand-icon" />
              CaseParser
            </span>
            <ul className="nav-links">
              <NavItem
                active={section === "dashboard"}
                onClick={() => handleSectionChange("dashboard")}
              >
                Дашборд
              </NavItem>
              <NavItem
                active={section === "cases"}
                onClick={() => handleSectionChange("cases")}
              >
                Кейсы
              </NavItem>
              <NavItem
                active={section === "analytics"}
                onClick={() => handleSectionChange("analytics")}
              >
                Аналитика
              </NavItem>
              <NavItem
                active={section === "portfolio"}
                onClick={() => handleSectionChange("portfolio")}
              >
                Портфель
              </NavItem>
            </ul>
          </div>
          <div className="navbar-right">
            <span className="navbar-text">
              Последнее обновление: {new Date().toLocaleTimeString()}
            </span>
            {user ? (
              <div className="user-area">
                <span className="user-name">{user.username}</span>
                <button className="btn btn-outline-light" onClick={handleLogout}>
                  <FaDoorOpen /> Выйти
                </button>
              </div>
            ) : (
              <div className="auth-buttons">
                <button
                  className="btn btn-outline-light"
                  onClick={() => openAuthModal("login")}
                >
                  <FaSignInAlt /> Войти
                </button>
                <button
                  className="btn btn-primary"
                  onClick={() => openAuthModal("register")}
                >
                  Регистрация
                </button>
              </div>
            )}
          </div>
        </div>
      </nav>

      <main className="container">
        {globalError && <div className="alert alert-danger">{globalError}</div>}
        {loading && (
          <div className="loading-overlay">
            <div className="spinner" />
            <span>Загрузка...</span>
          </div>
        )}

        {section === "dashboard" && renderDashboard()}
        {section === "cases" && renderCases()}
        {section === "analytics" && renderAnalytics()}
        {section === "portfolio" && renderPortfolio()}
      </main>

      {authModal.open && (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <div className="modal-content auth-modal">
            <div className="modal-header">
              <h5 className="card-title">
                {authModal.mode === "login" ? "Вход" : "Регистрация"}
              </h5>
              <button className="btn btn-outline-light" onClick={closeAuthModal}>
                ✕
              </button>
            </div>
            <form onSubmit={handleAuthSubmit}>
              <div className="modal-body">
                {authModal.mode === "register" && (
                  <div className="form-group">
                    <label htmlFor="username">Имя пользователя</label>
                    <input id="username" name="username" type="text" required />
                  </div>
                )}
                <div className="form-group">
                  <label htmlFor="email">Email</label>
                  <input id="email" name="email" type="email" required />
                </div>
                <div className="form-group">
                  <label htmlFor="password">Пароль</label>
                  <input id="password" name="password" type="password" required />
                </div>
                {authModal.error && (
                  <div className="alert alert-danger">{authModal.error}</div>
                )}
              </div>
              <div className="modal-footer">
                <button type="submit" className="btn btn-primary">
                  {authModal.mode === "login" ? "Войти" : "Зарегистрироваться"}
                </button>
                <button
                  type="button"
                  className="btn btn-outline-light"
                  onClick={() =>
                    setAuthModal((prev) => ({
                      open: true,
                      mode: prev.mode === "login" ? "register" : "login",
                    }))
                  }
                >
                  {authModal.mode === "login"
                    ? "Нет аккаунта?"
                    : "Уже есть аккаунт?"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  accent: "primary" | "info" | "success" | "warning";
}

const StatCard = ({ icon, label, value, accent }: StatCardProps) => (
  <div className={clsx("card stat-card", `accent-${accent}`)}>
    <div className="card-body">
      <div className="stat-icon">{icon}</div>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  </div>
);

interface TopListProps {
  title: string;
  items: TopMover[];
  tone: "success" | "danger";
}

const TopList = ({ title, items, tone }: TopListProps) => (
  <div className="card">
    <div className="card-header">
      <h5 className="card-title">{title}</h5>
    </div>
    <div className="card-body">
      {items.length === 0 ? (
        <div className="empty-state">Нет данных</div>
      ) : (
        <ul className="list-unstyled">
          {items.map((item) => (
            <li key={item.case_id} className="list-item">
              <div>
                <strong>{item.name}</strong>
                <div className="text-muted small">
                  {formatCurrency(item.current_price)}
                </div>
              </div>
              <div className={clsx("badge", `tone-${tone}`)}>
                {formatPercent(item.price_change)}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  </div>
);

interface SentimentWidgetProps {
  overview: MarketOverview | null;
}

const SentimentWidget = ({ overview }: SentimentWidgetProps) => {
  if (!overview) {
    return <div className="empty-state">Нет данных</div>;
  }
  const sentiment = sentimentLabel[overview.market_sentiment] ?? sentimentLabel.neutral;
  return (
    <div className="sentiment-widget">
      <div className="sentiment-icon" style={{ color: sentiment.color }}>
        {sentiment.icon}
      </div>
      <div>
        <h4 style={{ color: sentiment.color }}>{sentiment.text}</h4>
        <p className="text-muted">На основе анализа 24 часовых изменений</p>
      </div>
    </div>
  );
};

interface NavItemProps {
  children: React.ReactNode;
  active: boolean;
  onClick: () => void;
}

const NavItem = ({ active, children, onClick }: NavItemProps) => (
  <li>
    <button
      className={clsx("nav-link-btn", { active })}
      onClick={onClick}
      type="button"
    >
      {children}
    </button>
  </li>
);

const getChangeClass = (value?: number | null) => {
  if (value === undefined || value === null) return "";
  if (value > 0) return "price-up";
  if (value < 0) return "price-down";
  return "price-neutral";
};

export default App;
