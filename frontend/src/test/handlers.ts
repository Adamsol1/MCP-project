import {http, HttpResponse} from 'msw';

export const handlers = [

  http.post('/api/import/upload', () => {
    return HttpResponse.json({status: "success", filename: "test.txt", path: "/uploads/test.txt"});
  })
]


