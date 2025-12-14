import { useState } from "react";
import { useList, useDelete, useNotification } from "@refinedev/core";
import { List } from "@refinedev/antd";
import { Button, Modal, Form, Input, Space, Typography } from "antd";
import { PlusOutlined } from "@ant-design/icons";

import { DatabaseList as DatabaseListComponent } from "../../components/DatabaseList";
import { handleApiError, getErrorMessage } from "../../utils/error";
import type { DatabaseInfo, DatabaseCreateRequest } from "../../types";

const { Text } = Typography;

const API_URL = "http://localhost:8000/api/v1";

export function DatabaseList() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const { open: notify } = useNotification();

  const { data, isLoading, refetch } = useList<DatabaseInfo>({
    resource: "dbs",
  });

  const { mutate: deleteOne } = useDelete();

  const databases = data?.data ?? [];

  const handleAdd = async (values: { name: string; url: string }) => {
    setLoading(true);
    try {
      const body: DatabaseCreateRequest = { url: values.url };
      const response = await fetch(`${API_URL}/dbs/${values.name}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        await handleApiError(response, "Failed to add database");
      }

      notify?.({
        type: "success",
        message: "Database added",
        description: `Successfully connected to ${values.name}`,
      });

      form.resetFields();
      setIsModalOpen(false);
      refetch();
    } catch (error) {
      notify?.({
        type: "error",
        message: "Failed to add database",
        description: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = (name: string) => {
    deleteOne(
      {
        resource: "dbs",
        id: name,
      },
      {
        onSuccess: () => {
          notify?.({
            type: "success",
            message: "Database deleted",
            description: `Connection ${name} has been removed`,
          });
          refetch();
        },
        onError: (error) => {
          notify?.({
            type: "error",
            message: "Failed to delete",
            description: getErrorMessage(error),
          });
        },
      }
    );
  };

  return (
    <List
      title="Database Connections"
      headerButtons={
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setIsModalOpen(true)}
        >
          Add Database
        </Button>
      }
    >
      <DatabaseListComponent
        databases={databases}
        loading={isLoading}
        onDelete={handleDelete}
      />

      <Modal
        title="Add Database Connection"
        open={isModalOpen}
        onCancel={() => setIsModalOpen(false)}
        footer={null}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" onFinish={handleAdd}>
          <Form.Item
            name="name"
            label="Connection Name"
            rules={[
              { required: true, message: "Please enter a name" },
              { pattern: /^[a-zA-Z][a-zA-Z0-9_-]*$/, message: "Must start with a letter, only alphanumeric and _-" },
            ]}
          >
            <Input placeholder="mydb" />
          </Form.Item>

          <Form.Item
            name="url"
            label="PostgreSQL URL"
            rules={[
              { required: true, message: "Please enter the connection URL" },
              {
                pattern: /^postgres(ql)?:\/\/.+/,
                message: "Must be a valid PostgreSQL URL",
              },
            ]}
          >
            <Input.Password
              placeholder="postgresql://user:password@host:5432/dbname"
              visibilityToggle
            />
          </Form.Item>

          <Text type="secondary" style={{ display: "block", marginBottom: 16 }}>
            The system will connect to the database and extract metadata.
          </Text>

          <Space style={{ width: "100%", justifyContent: "flex-end" }}>
            <Button onClick={() => setIsModalOpen(false)}>Cancel</Button>
            <Button type="primary" htmlType="submit" loading={loading}>
              Connect
            </Button>
          </Space>
        </Form>
      </Modal>
    </List>
  );
}
