import { useState } from "react";
import { Layout, Menu, Button, theme } from "antd";
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  DatabaseOutlined,
} from "@ant-design/icons";
import { useMenu, useLink } from "@refinedev/core";
import type { MenuProps } from "antd";

const { Sider } = Layout;

/**
 * Custom Sider component that uses antd Menu `items` prop
 * instead of deprecated `children` prop to avoid console warnings.
 */
export function CustomSider() {
  const [collapsed, setCollapsed] = useState(false);
  const { menuItems, selectedKey } = useMenu();
  const { token } = theme.useToken();
  const Link = useLink();

  // Convert refine menu items to antd Menu items format
  const items: MenuProps["items"] = menuItems.map((item) => ({
    key: item.key,
    icon: item.icon,
    label: (
      <Link to={item.route ?? "/"} style={{ textDecoration: "none" }}>
        {item.label}
      </Link>
    ),
  }));

  return (
    <Sider
      collapsible
      collapsed={collapsed}
      onCollapse={setCollapsed}
      trigger={null}
      style={{
        backgroundColor: token.colorBgContainer,
        borderRight: `1px solid ${token.colorBorderSecondary}`,
      }}
    >
      {/* Title Section */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: collapsed ? "center" : "flex-start",
          gap: 8,
          padding: collapsed ? "16px 0" : "16px",
          borderBottom: `1px solid ${token.colorBorderSecondary}`,
        }}
      >
        <DatabaseOutlined style={{ fontSize: 24, color: token.colorPrimary }} />
        {!collapsed && (
          <span style={{ fontWeight: 600, fontSize: 16 }}>DB Query Tool</span>
        )}
      </div>

      {/* Menu */}
      <Menu
        mode="inline"
        selectedKeys={selectedKey ? [selectedKey] : []}
        items={items}
        style={{
          borderRight: 0,
          backgroundColor: "transparent",
        }}
      />

      {/* Collapse Toggle Button */}
      <Button
        type="text"
        icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
        onClick={() => setCollapsed(!collapsed)}
        style={{
          position: "absolute",
          bottom: 16,
          left: "50%",
          transform: "translateX(-50%)",
        }}
      />
    </Sider>
  );
}
