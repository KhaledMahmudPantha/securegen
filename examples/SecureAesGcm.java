public class Main {
  public static void main(String[] args) throws Exception {
    byte[] plaintext = "hello".getBytes(java.nio.charset.StandardCharsets.UTF_8);
    byte[] keyBytes = new byte[16];
    java.security.SecureRandom sr = new java.security.SecureRandom();
    sr.nextBytes(keyBytes);
    javax.crypto.SecretKey key = new javax.crypto.spec.SecretKeySpec(keyBytes, "AES");
    byte[] iv = new byte[12];
    sr.nextBytes(iv);
    javax.crypto.Cipher cipher = javax.crypto.Cipher.getInstance("AES/GCM/NoPadding");
    cipher.init(javax.crypto.Cipher.ENCRYPT_MODE, key, new javax.crypto.spec.GCMParameterSpec(128, iv));
    byte[] out = cipher.doFinal(plaintext);
    System.out.println(java.util.Base64.getEncoder().encodeToString(out));
  }
}
