import axios from 'axios';

const API_BACKEND_URL = 'http://localhost:8000'; //Backend server URL

export async function uploadFile(file: File){

  //Save file data
  const formData = new FormData();

  formData.append('file', file);

  const httpResponse = await axios.post(
    `${API_BACKEND_URL}/api/import/upload`,
    formData
  );

  return httpResponse.data;

}
