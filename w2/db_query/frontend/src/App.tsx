import { Refine } from "@refinedev/core";
import { RefineThemes, useNotificationProvider } from "@refinedev/antd";
import routerProvider, {
  DocumentTitleHandler,
  UnsavedChangesNotifier,
} from "@refinedev/react-router-v6";
import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import { ConfigProvider, App as AntdApp, Layout as AntdLayout } from "antd";
import { DatabaseOutlined, CodeOutlined } from "@ant-design/icons";

import { dataProvider } from "./providers/dataProvider";
import { DatabaseList } from "./pages/databases/list";
import { DatabaseShow } from "./pages/databases/show";
import { QueryPage } from "./pages/query";
import { CustomSider } from "./components/CustomSider";

import "./index.css";

function Layout() {
  return (
    <AntdLayout style={{ minHeight: "100vh" }}>
      <CustomSider />
      <AntdLayout>
        <AntdLayout.Content style={{ padding: 24 }}>
          <Outlet />
        </AntdLayout.Content>
      </AntdLayout>
    </AntdLayout>
  );
}

function App() {
  return (
    <BrowserRouter
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <ConfigProvider theme={RefineThemes.Blue}>
        <AntdApp>
          <Refine
            dataProvider={dataProvider}
            routerProvider={routerProvider}
            notificationProvider={useNotificationProvider}
            resources={[
              {
                name: "dbs",
                list: "/databases",
                show: "/databases/:id",
                meta: {
                  label: "Databases",
                  icon: <DatabaseOutlined />,
                },
              },
              {
                name: "query",
                list: "/query",
                meta: {
                  label: "Query",
                  icon: <CodeOutlined />,
                },
              },
            ]}
            options={{
              syncWithLocation: true,
              warnWhenUnsavedChanges: true,
            }}
          >
            <Routes>
              <Route element={<Layout />}>
                <Route index element={<Navigate to="/databases" replace />} />
                <Route path="/databases" element={<DatabaseList />} />
                <Route path="/databases/:id" element={<DatabaseShow />} />
                <Route path="/query" element={<QueryPage />} />
                <Route path="/query/:dbName" element={<QueryPage />} />
                <Route path="*" element={<Navigate to="/databases" replace />} />
              </Route>
            </Routes>
            <UnsavedChangesNotifier />
            <DocumentTitleHandler />
          </Refine>
        </AntdApp>
      </ConfigProvider>
    </BrowserRouter>
  );
}

export default App;
