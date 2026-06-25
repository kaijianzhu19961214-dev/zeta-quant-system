FROM node:22-alpine

WORKDIR /app

COPY apps/quant_ops_web/package.json apps/quant_ops_web/package-lock.json ./

RUN npm ci

COPY apps/quant_ops_web .

EXPOSE 5173

CMD ["npm", "run", "dev"]
