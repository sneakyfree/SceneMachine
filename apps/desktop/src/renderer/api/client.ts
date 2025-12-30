/**
 * API client for communicating with the Python backend.
 */

import type { Project } from '@shared/types';

/**
 * API client singleton for backend communication.
 */
class APIClient {
  /**
   * Send a request to the backend via IPC.
   */
  private async request<T>(method: string, params?: Record<string, unknown>): Promise<T> {
    try {
      const result = await window.electronAPI.backendRequest<T>(method, params);
      return result;
    } catch (error) {
      console.error(`API Error [${method}]:`, error);
      throw error;
    }
  }

  // ============ Projects ============

  /**
   * List all projects.
   */
  async listProjects(): Promise<Project[]> {
    return this.request<Project[]>('projects.list');
  }

  /**
   * Get a project by ID.
   */
  async getProject(id: string): Promise<Project> {
    return this.request<Project>('projects.get', { id });
  }

  /**
   * Create a new project.
   */
  async createProject(data: {
    name: string;
    description?: string;
    settings?: Record<string, unknown>;
  }): Promise<Project> {
    return this.request<Project>('projects.create', data);
  }

  /**
   * Update a project.
   */
  async updateProject(
    id: string,
    data: {
      name?: string;
      description?: string;
      settings?: Record<string, unknown>;
    }
  ): Promise<Project> {
    return this.request<Project>('projects.update', { id, ...data });
  }

  /**
   * Delete a project.
   */
  async deleteProject(id: string): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>('projects.delete', { id });
  }

  // ============ Utility ============

  /**
   * Ping the backend.
   */
  async ping(): Promise<{ status: string }> {
    return this.request<{ status: string }>('ping');
  }

  /**
   * Get backend version.
   */
  async getVersion(): Promise<{ version: string; environment: string }> {
    return this.request<{ version: string; environment: string }>('version');
  }
}

// Export singleton instance
export const api = new APIClient();
