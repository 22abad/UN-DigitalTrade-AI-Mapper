# ============================================================
# Stage 1: Build — compile the Spring Boot application into a JAR
# ============================================================
FROM eclipse-temurin:17-jdk AS build

WORKDIR /app

# Copy Maven wrapper and pom.xml first so dependency download is cached
COPY .mvn .mvn
COPY mvnw pom.xml ./
RUN chmod +x mvnw && ./mvnw -q dependency:go-offline

# Copy source code and build the fat JAR (skip tests for faster builds)
COPY src src
RUN ./mvnw -q package -DskipTests

# ============================================================
# Stage 2: Runtime — run the built JAR on a minimal JRE image
# ============================================================
FROM eclipse-temurin:17-jre

WORKDIR /app

# Create a non-root user for security hardening
RUN addgroup --system app && adduser --system --ingroup app app

# Copy only the final JAR from the build stage
COPY --from=build /app/target/*.jar app.jar

# Drop root privileges
USER app

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
