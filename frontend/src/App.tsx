import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import MainLayout from '@/components/layout/MainLayout'
import Dashboard from '@/pages/Dashboard'
import Cases from '@/pages/Cases'
import Executions from '@/pages/Executions'
import Devices from '@/pages/Devices'
import Reports from '@/pages/Reports'
import Settings from '@/pages/Settings'

function App() {
  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#3B82F6',
          colorBgContainer: '#FFFFFF',
          colorText: '#1E293B',
        },
      }}
    >
      <BrowserRouter>
        <MainLayout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/cases" element={<Cases />} />
            <Route path="/executions" element={<Executions />} />
            <Route path="/devices" element={<Devices />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </MainLayout>
      </BrowserRouter>
    </ConfigProvider>
  )
}

export default App
