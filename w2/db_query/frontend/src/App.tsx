import { Refine } from "@refinedev/core";
import { RefineThemes, ThemedLayoutV2, useNotificationProvider } from "@refinedev/antd";
import routerProvider, {
  DocumentTitleHandler,
  UnsavedChangesNotifier,
} from "@refinedev/react-router-v6";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider, App as AntdApp } from "antd";
import { DatabaseOutlined, CodeOutlined } from "@ant-design/icons";

import { dataProvider } from "./providers/dataProvider";
import { DatabaseList } from "./pages/databases/list";
import { DatabaseShow } from "./pages/databases/show";
import { QueryPage } from "./pages/query";

import "./index.css";

function App() {
  return (
    <BrowserRouter>
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
              <Route
                element={
                  <ThemedLayoutV2
                    Title={() => (
                      <div style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "0 8px"
                      }}>
                        <DatabaseOutlined style={{ fontSize: 24 }} />
                        <span style={{ fontWeight: 600, fontSize: 16 }}>
                          DB Query Tool
                        </span>
                      </div>
                    )}
                  >
                    <Routes>
                      <Route index element={<Navigate to="/databases" />} />
                      <Route path="/databases" element={<DatabaseList />} />
                      <Route path="/databases/:id" element={<DatabaseShow />} />
                      <Route path="/query" element={<QueryPage />} />
                      <Route path="/query/:dbName" element={<QueryPage />} />
                    </Routes>
                  </ThemedLayoutV2>
                }
              >
                <Route path="*" element={<Navigate to="/databases" />} />
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
