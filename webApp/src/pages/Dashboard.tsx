export default function Dashboard() {
  return (
    <div className="min-h-screen bg-ui-bg">
      <header className="bg-ui-element-bg shadow">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-text-primary">Dashboard</h1>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Focus Timer Card */}
          <div className="bg-ui-element-bg rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-text-primary mb-4">Focus Timer</h2>
            <div className="text-center">
              <div className="text-4xl font-bold text-brand-primary mb-2">25:00</div>
              <button className="bg-brand-primary text-brand-primary-text px-4 py-2 rounded-lg hover:bg-brand-primary-hover transition-colors">
                Start Session
              </button>
            </div>
          </div>

          {/* Tasks Card */}
          <div className="bg-ui-element-bg rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-text-primary mb-4">Today's Tasks</h2>
            <div className="space-y-2">
              <div className="flex items-center">
                <input type="checkbox" className="mr-2" />
                <span className="text-text-secondary">Review project proposal</span>
              </div>
              <div className="flex items-center">
                <input type="checkbox" className="mr-2" />
                <span className="text-text-secondary">Team standup meeting</span>
              </div>
              <div className="flex items-center">
                <input type="checkbox" className="mr-2" />
                <span className="text-text-secondary">Update documentation</span>
              </div>
            </div>
          </div>

          {/* AI Coach Card */}
          <div className="bg-ui-element-bg rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-text-primary mb-4">AI Coach</h2>
            <div className="space-y-4">
              <p className="text-text-muted">
                Ready to help you stay focused and productive. What would you like to work on?
              </p>
              <button className="w-full bg-ui-interactive-bg text-text-secondary px-4 py-2 rounded-lg hover:bg-ui-interactive-bg-hover transition-colors">
                Start Chat
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
} 